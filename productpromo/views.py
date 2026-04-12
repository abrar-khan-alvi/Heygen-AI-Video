"""
productpromo/views.py

10 REST endpoints for the product promotional video flow.
All endpoints are namespaced under /api/v1/product-promo/ — zero collision
with videogen endpoints.

Flow:
  POST   /projects/                          → 1. Create project
  POST   /projects/<uuid>/upload-image/      → 2. Upload product image
  PATCH  /projects/<uuid>/                   → 3. Select avatar
  POST   /projects/<uuid>/generate-script/   → 4. AI generates script (Gemini multimodal)
  PUT    /projects/<uuid>/finalize-script/   → 5. Confirm / edit script
  POST   /projects/<uuid>/generate-video/    → 6. Trigger HeyGen
  GET    /projects/<uuid>/video-status/      → 7. Poll video status
  GET    /projects/                          → 8. List projects
  GET    /projects/<uuid>/                   → 9. Project detail
  DELETE /projects/<uuid>/                   → 10. Delete project

Avatar browsing → use existing videogen endpoints:
  GET /api/v1/videogen/options/avatars/
  GET /api/v1/videogen/options/voices/
"""

import logging
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import ProductPromoProject
from .serializers import (
    PromoProjectCreateSerializer,
    PromoProjectUpdateSerializer,
    PromoScriptFinalizeSerializer,
    ProductPromoProjectSerializer,
    ProductPromoProjectListSerializer,
)
from .permissions import IsPromoProjectOwner

# CachedAvatar is imported from videogen — read-only reference, no duplication
from videogen.models import CachedAvatar

logger = logging.getLogger(__name__)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_project(project_id, user=None) -> ProductPromoProject | None:
    filters = {"id": project_id}
    if user:
        filters["user"] = user
    try:
        return ProductPromoProject.objects.select_related("user").get(**filters)
    except ProductPromoProject.DoesNotExist:
        return None


def _ctx(request):
    return {"request": request}


EDITABLE_STATUSES = [
    ProductPromoProject.StatusChoice.DRAFT,
    ProductPromoProject.StatusChoice.SCRIPT_GENERATED,
    ProductPromoProject.StatusChoice.SCRIPT_FINALIZED,
]


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CREATE PROJECT
# POST /api/v1/product-promo/projects/
# Body: { "product_name": "...", "product_description": "..." }
# ═══════════════════════════════════════════════════════════════════════════════

class PromoProjectCreateView(APIView):
    """Create a new product promo project (Step 1)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PromoProjectCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        project = ProductPromoProject.objects.create(
            user=request.user,
            product_name=d["product_name"],
            product_description=d["product_description"],
        )
        return Response(
            ProductPromoProjectSerializer(project, context=_ctx(request)).data,
            status=status.HTTP_201_CREATED,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 2. UPLOAD PRODUCT IMAGE
# POST /api/v1/product-promo/projects/<uuid>/upload-image/
# Content-Type: multipart/form-data   field: "image"
# ═══════════════════════════════════════════════════════════════════════════════

class PromoImageUploadView(APIView):
    """
    Upload (or replace) the product image for a project.
    Accepts multipart/form-data with an 'image' file field.
    Max size: 10 MB. Allowed types: image/jpeg, image/png, image/webp.
    """
    permission_classes = [IsAuthenticated, IsPromoProjectOwner]
    parser_classes     = [MultiPartParser, FormParser]

    ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
    MAX_BYTES          = 10 * 1024 * 1024  # 10 MB

    def post(self, request, project_id):
        project = _get_project(project_id)
        if not project:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, project)

        if project.status not in EDITABLE_STATUSES:
            return Response(
                {"detail": f"Cannot upload image for project in '{project.status}' status."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        image_file = request.FILES.get("image")
        if not image_file:
            return Response({"detail": "No 'image' file provided."}, status=status.HTTP_400_BAD_REQUEST)

        if image_file.content_type not in self.ALLOWED_MIME_TYPES:
            return Response(
                {"detail": f"Unsupported image type '{image_file.content_type}'. "
                           f"Use JPEG, PNG, or WebP."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if image_file.size > self.MAX_BYTES:
            return Response(
                {"detail": "Image too large. Maximum size is 10 MB."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Delete old image file from storage before saving new one
        if project.product_image:
            try:
                project.product_image.delete(save=False)
            except Exception:
                pass

        project.product_image = image_file
        # If user uploads a new image after script was generated, reset script
        if project.status in (
            ProductPromoProject.StatusChoice.SCRIPT_GENERATED,
            ProductPromoProject.StatusChoice.SCRIPT_FINALIZED,
        ):
            project.status = ProductPromoProject.StatusChoice.DRAFT
            project.generated_script = ""
            project.finalized_script = ""
        project.save()

        return Response(ProductPromoProjectSerializer(project, context=_ctx(request)).data)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. UPDATE PROJECT (avatar selection / product field edits)
# PATCH /api/v1/product-promo/projects/<uuid>/
# Body: { "avatar_id": "..." }   or   { "product_name": "..." }
# ═══════════════════════════════════════════════════════════════════════════════

class PromoProjectUpdateView(APIView):
    """
    PATCH — update avatar, voice, or product fields.
    Avatar details are auto-populated from the CachedAvatar cache.
    """
    permission_classes = [IsAuthenticated, IsPromoProjectOwner]

    def patch(self, request, project_id):
        project = _get_project(project_id)
        if not project:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, project)

        if project.status not in EDITABLE_STATUSES:
            return Response(
                {"detail": f"Cannot update project in '{project.status}' status."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PromoProjectUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        # Update product fields
        if "product_name" in d:
            project.product_name = d["product_name"]
        if "product_description" in d:
            project.product_description = d["product_description"]

        # Avatar — auto-populate name, gender, preview from CachedAvatar
        if "avatar_id" in d:
            avatar_id = d["avatar_id"]
            project.avatar_id = avatar_id
            try:
                cached = CachedAvatar.objects.get(avatar_id=avatar_id, is_active=True)
                project.avatar_name        = cached.avatar_name
                project.avatar_gender      = cached.gender
                project.avatar_preview_url = cached.preview_image_url
                # Auto-select default voice unless overridden
                if "voice_id" not in d:
                    project.voice_id = cached.default_voice_id
            except CachedAvatar.DoesNotExist:
                logger.warning(f"Avatar {avatar_id} not found in CachedAvatar")
                project.avatar_name   = ""
                project.avatar_gender = ""

        # Explicit voice override
        if "voice_id" in d:
            project.voice_id = d["voice_id"]

        # Changing avatar/product after script generation → reset script
        if project.status in (
            ProductPromoProject.StatusChoice.SCRIPT_GENERATED,
            ProductPromoProject.StatusChoice.SCRIPT_FINALIZED,
        ):
            project.status           = ProductPromoProject.StatusChoice.DRAFT
            project.generated_script = ""
            project.finalized_script  = ""

        project.save()
        return Response(ProductPromoProjectSerializer(project, context=_ctx(request)).data)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. GENERATE SCRIPT  (Gemini multimodal — product context)
# POST /api/v1/product-promo/projects/<uuid>/generate-script/
# No body required — uses saved project fields + product_image path
# ═══════════════════════════════════════════════════════════════════════════════

class PromoScriptGenerateView(APIView):
    """
    Generate a product promotional script via Gemini.

    - Uses product_name, product_description, avatar_gender from the project.
    - If product_image is uploaded, sends it to Gemini as multimodal input
      so Gemini can visually reference the product appearance.
    - Context is 100% product-specific — no industry/background fields.

    This is INDEPENDENT from videogen's ScriptGenerateView.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        project = _get_project(project_id, user=request.user)
        if not project:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)

        # Validate required fields
        missing = []
        if not project.product_name:
            missing.append("product_name")
        if not project.product_description:
            missing.append("product_description")
        if not project.avatar_id:
            missing.append("avatar_id (PATCH the project first to select an avatar)")
        if missing:
            return Response(
                {"detail": f"Complete these fields first: {', '.join(missing)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        allowed = [
            ProductPromoProject.StatusChoice.DRAFT,
            ProductPromoProject.StatusChoice.SCRIPT_GENERATED,
        ]
        if project.status not in allowed:
            return Response(
                {"detail": f"Cannot generate script in '{project.status}' status."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Resolve absolute path to product image (if uploaded)
        image_path = None
        if project.product_image:
            try:
                image_path = project.product_image.path
            except Exception:
                image_path = None  # storage backend doesn't support .path → text-only fallback

        from .services.gemini_service import generate_product_script

        try:
            script = generate_product_script(
                product_name=project.product_name,
                product_description=project.product_description,
                avatar_gender=project.avatar_gender or "professional",
                image_path=image_path,
            )
        except Exception as e:
            return Response(
                {"detail": f"Script generation failed: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        project.generated_script = script
        project.finalized_script  = ""  # clear old finalized on regenerate
        project.status            = ProductPromoProject.StatusChoice.SCRIPT_GENERATED
        project.save()

        return Response({
            "project_id":       str(project.id),
            "generated_script": script,
            "mode":             "multimodal" if image_path else "text-only",
            "project":          ProductPromoProjectSerializer(project, context=_ctx(request)).data,
        })


# ═══════════════════════════════════════════════════════════════════════════════
# 5. FINALIZE SCRIPT  (product-specific finalization)
# PUT /api/v1/product-promo/projects/<uuid>/finalize-script/
# Body: { "finalized_script": "..." }
# ═══════════════════════════════════════════════════════════════════════════════

class PromoScriptFinalizeView(APIView):
    """
    Confirm (and optionally edit) the generated script.
    After this step the project is ready for video generation.

    This is INDEPENDENT from videogen's ScriptFinalizeView.
    Different model, different context, different URL prefix.
    """
    permission_classes = [IsAuthenticated, IsPromoProjectOwner]

    def put(self, request, project_id):
        project = _get_project(project_id)
        if not project:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, project)

        blocked = [
            ProductPromoProject.StatusChoice.DRAFT,
            ProductPromoProject.StatusChoice.VIDEO_PROCESSING,
            ProductPromoProject.StatusChoice.VIDEO_COMPLETED,
        ]
        if project.status in blocked:
            return Response(
                {"detail": f"Cannot finalize script in '{project.status}' status. "
                           f"Generate a script first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PromoScriptFinalizeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        project.finalized_script = serializer.validated_data["finalized_script"]
        project.status           = ProductPromoProject.StatusChoice.SCRIPT_FINALIZED
        project.save()

        return Response(ProductPromoProjectSerializer(project, context=_ctx(request)).data)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. GENERATE VIDEO  (HeyGen Video Agent — product prompt)
# POST /api/v1/product-promo/projects/<uuid>/generate-video/
# ═══════════════════════════════════════════════════════════════════════════════

class PromoVideoGenerateView(APIView):
    """
    Submit the video generation job to HeyGen.
    Uses a product-specific prompt builder (not the service/marketing prompt
    from videogen).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        project = _get_project(project_id, user=request.user)
        if not project:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)

        if project.status == ProductPromoProject.StatusChoice.VIDEO_PROCESSING:
            return Response(
                {"detail": "Video is already being generated. Please check the status view for updates."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if project.status == ProductPromoProject.StatusChoice.VIDEO_COMPLETED:
            return Response(
                {"detail": "Video generation is already complete for this project."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Allow generation only if freshly finalized or if a previous attempt failed
        allowed_to_generate = [
            ProductPromoProject.StatusChoice.SCRIPT_FINALIZED,
            ProductPromoProject.StatusChoice.VIDEO_FAILED,
        ]
        if project.status not in allowed_to_generate:
            return Response(
                {"detail": "Finalize the script first before generating the video."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not project.avatar_id:
            return Response({"detail": "No avatar selected."}, status=status.HTTP_400_BAD_REQUEST)

        from .services.heygen_service import generate_product_video

        # Pass physical file path for asset upload if image exists
        product_image_path = None
        if project.product_image:
            try:
                product_image_path = project.product_image.path
            except Exception:
                product_image_path = None

        try:
            result = generate_product_video(
                avatar_id=project.avatar_id,
                voice_id=project.voice_id,
                script=project.finalized_script,
                product_name=project.product_name,
                product_description=project.product_description,
                avatar_gender=project.avatar_gender or "professional",
                product_image_path=product_image_path,
            )
        except Exception as e:
            project.status               = ProductPromoProject.StatusChoice.VIDEO_FAILED
            project.video_status_message = str(e)[:500]
            project.save()
            return Response(
                {"detail": f"Video generation failed: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        project.heygen_video_id = result["video_id"]
        project.status          = ProductPromoProject.StatusChoice.VIDEO_PROCESSING
        project.video_status_message = "Video queued with HeyGen."
        project.save()

        # Kick off background monitoring
        from django.core.cache import cache
        lock_key = f"promo_task_lock_{project.id}"
        if not cache.get(lock_key):
            from .tasks import monitor_promo_video_task
            cache.set(lock_key, True, timeout=600)
            monitor_promo_video_task.delay(str(project.id))
            logger.info(f"Promo monitoring task started for project {project.id}")

        return Response({
            "project_id":     str(project.id),
            "heygen_video_id": result["video_id"],
            "status":         "processing",
            "message":        "Product promo video queued. Poll /video-status/ for updates.",
        })


# ═══════════════════════════════════════════════════════════════════════════════
# 7. VIDEO STATUS POLL
# GET /api/v1/product-promo/projects/<uuid>/video-status/
# ═══════════════════════════════════════════════════════════════════════════════

class PromoVideoStatusView(APIView):
    """Poll current video processing status from HeyGen."""
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = _get_project(project_id, user=request.user)
        if not project:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)

        if not project.heygen_video_id:
            return Response(
                {"detail": "No video has been generated yet."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Ensure monitoring task is running
        if project.status == ProductPromoProject.StatusChoice.VIDEO_PROCESSING:
            from django.core.cache import cache
            lock_key = f"promo_task_lock_{project.id}"
            if not cache.get(lock_key):
                from .tasks import monitor_promo_video_task
                cache.set(lock_key, True, timeout=600)
                monitor_promo_video_task.delay(str(project.id))

        from .services.heygen_service import get_video_status

        try:
            result = get_video_status(project.heygen_video_id)
        except Exception as e:
            return Response(
                {"detail": f"Status check failed: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if result["status"] == "completed":
            project.status    = ProductPromoProject.StatusChoice.VIDEO_COMPLETED
            project.video_url = result.get("video_url") or ""
            
            # Use same messaging as videogen to manage expectations for local file download
            if not project.video_file:
                project.video_status_message = "Video completed. Processing final file..."
            else:
                project.video_status_message = "Video fully processed."
        elif result["status"] == "failed":
            project.status = ProductPromoProject.StatusChoice.VIDEO_FAILED
            project.video_status_message = result.get("message", "Video generation failed.")
        else:
            project.video_status_message = result.get("message") or f"Status: {result['status']}"

        project.save()

        return Response({
            "project_id":    str(project.id),
            "status":        project.status,
            "video_url":     project.video_url or None,
            "video_file_url": (
                request.build_absolute_uri(project.video_file.url)
                if project.video_file else None
            ),
            "message": project.video_status_message,
        })


# ═══════════════════════════════════════════════════════════════════════════════
# 8 & 9. LIST + DETAIL
# GET /api/v1/product-promo/projects/
# GET /api/v1/product-promo/projects/<uuid>/
# ═══════════════════════════════════════════════════════════════════════════════

class PromoProjectListView(generics.ListAPIView):
    serializer_class   = ProductPromoProjectListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ProductPromoProject.objects.filter(user=self.request.user)

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx


class PromoProjectDetailView(APIView):
    permission_classes = [IsAuthenticated, IsPromoProjectOwner]

    def get(self, request, project_id):
        project = _get_project(project_id)
        if not project:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, project)
        return Response(ProductPromoProjectSerializer(project, context=_ctx(request)).data)

    # ── 10. DELETE ────────────────────────────────────────────────────────────
    def delete(self, request, project_id):
        project = _get_project(project_id)
        if not project:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, project)
        project.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
