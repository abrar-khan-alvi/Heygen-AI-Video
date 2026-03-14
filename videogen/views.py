import random
import logging
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.pagination import CursorPagination

from .models import VideoProject, Industry, Background, CachedAvatar, CachedVoice
from .serializers import (
    IndustrySerializer,
    BackgroundSerializer,
    CachedAvatarSerializer,
    CachedVoiceSerializer,
    ProjectCreateSerializer,
    ProjectPatchSerializer,
    ScriptFinalizeSerializer,
    VideoProjectSerializer,
    VideoProjectListSerializer,
)
from .permissions import IsProjectOwner
from .services import heygen_service, gemini_service
from subscriptions.permissions import (
    HasActiveSubscription,
    CanGenerateScript,
    CanGenerateVideo,
)

logger = logging.getLogger(__name__)


def _get_project(project_id, user=None):
    filters = {"id": project_id}
    if user:
        filters["user"] = user
    try:
        return VideoProject.objects.select_related("user").get(**filters)
    except VideoProject.DoesNotExist:
        return None


def _ctx(request):
    return {"request": request}


class ProjectCursorPagination(CursorPagination):
    page_size = 20
    ordering = "-created_at"
    cursor_query_param = "cursor"


# ═══════════════════════════════════════════════════════════════════════════════
# OPTIONS ENDPOINTS (no auth, instant from DB)
# ═══════════════════════════════════════════════════════════════════════════════

class IndustryListView(APIView):
    """GET /api/v1/videogen/options/industries/"""
    permission_classes = [AllowAny]

    def get(self, request):
        industries = Industry.objects.filter(is_active=True)
        return Response(IndustrySerializer(industries, many=True).data)


class BackgroundListView(APIView):
    """GET /api/v1/videogen/options/backgrounds/"""
    permission_classes = [AllowAny]

    def get(self, request):
        backgrounds = Background.objects.filter(is_active=True)
        return Response(BackgroundSerializer(backgrounds, many=True).data)


class AvatarBrowseView(APIView):
    """
    GET /api/v1/videogen/options/avatars/

    Without query params → returns 2 random avatars per category (for homepage preview).

    With ?category=<cat>  → returns ALL avatars in that category.
    With ?gender=<gender> → additionally filter by male / female.

    Examples:
      /options/avatars/                          # 2 random per category
      /options/avatars/?category=business        # all business avatars
      /options/avatars/?category=casual&gender=female

    Response (no filter):
    {
        "business": [{...}, ...],
        "casual":   [{...}, ...],
        ...
    }

    Response (with ?category=):
    {
        "category": "business",
        "gender": null,
        "count": 12,
        "avatars": [{...}, ...]
    }
    """
    permission_classes = [AllowAny]

    VALID_CATEGORIES = CachedAvatar.OutfitCategory.values
    VALID_GENDERS = [g.value for g in CachedAvatar.GenderChoice]

    def get(self, request):
        category = request.query_params.get("category", "").lower().strip()
        gender = request.query_params.get("gender", "").lower().strip()

        # ── Validate query params ────────────────────────────────────────
        if category and category not in self.VALID_CATEGORIES:
            return Response(
                {
                    "detail": f"Invalid category '{category}'.",
                    "valid_categories": self.VALID_CATEGORIES,
                },
                status=400,
            )

        if gender and gender not in self.VALID_GENDERS:
            return Response(
                {
                    "detail": f"Invalid gender '{gender}'.",
                    "valid_genders": self.VALID_GENDERS,
                },
                status=400,
            )

        qs = CachedAvatar.objects.filter(is_active=True)

        # ── Filtered mode: return all avatars for the given category ─────
        if category:
            qs = qs.filter(outfit_category=category)
            if gender:
                qs = qs.filter(gender=gender)
            avatars = list(qs.order_by("avatar_name"))
            return Response({
                "category": category,
                "gender": gender or None,
                "count": len(avatars),
                "avatars": CachedAvatarSerializer(avatars, many=True).data,
            })

        # ── Default mode: 2 random per category (preview) ───────────────
        result = {}
        for cat in self.VALID_CATEGORIES:
            avatars_in_category = list(qs.filter(outfit_category=cat))
            if avatars_in_category:
                picked = random.sample(
                    avatars_in_category,
                    min(2, len(avatars_in_category)),
                )
                result[cat] = CachedAvatarSerializer(picked, many=True).data

        return Response(result)


class AvatarDetailView(APIView):
    """
    GET /api/v1/videogen/options/avatars/<avatar_id>/

    Returns full details for a single avatar by its HeyGen avatar_id.
    """
    permission_classes = [AllowAny]

    def get(self, request, avatar_id):
        try:
            avatar = CachedAvatar.objects.get(avatar_id=avatar_id, is_active=True)
        except CachedAvatar.DoesNotExist:
            return Response({"detail": "Avatar not found."}, status=404)
        return Response(CachedAvatarSerializer(avatar).data)


class VoiceListView(APIView):
    """
    GET /api/v1/videogen/options/voices/

    Returns all synced voices from the HeyGen voice library.

    Optional query params:
      ?language_code=en-US   filter by language code
      ?gender=male|female    filter by gender

    Response:
    [
        {"voice_id": "...", "name": "...", "language": "...",
         "language_code": "...", "gender": "...", "preview_audio_url": "..."},
        ...
    ]
    """
    permission_classes = [AllowAny]

    def get(self, request):
        qs = CachedVoice.objects.filter(is_active=True)

        language_code = request.query_params.get("language_code", "").strip()
        gender = request.query_params.get("gender", "").lower().strip()

        if language_code:
            qs = qs.filter(language_code__iexact=language_code)
        if gender:
            qs = qs.filter(gender__iexact=gender)

        return Response(CachedVoiceSerializer(qs, many=True).data)


class TextToSpeechView(APIView):
    """
    POST /api/v1/videogen/tts/

    Preview a script using a selected voice (text-to-speech).
    Returns an audio URL you can play directly in the browser.

    Body (option A — explicit text):
        {
            "voice_id": "abc123",
            "text": "Hello, this is a preview of your script.",
            "speed": "1.0"      (optional, default "1")
            "language": "en"    (optional)
            "locale": "en-US"   (optional)
        }

    Body (option B — use project's generated/finalized script):
        {
            "voice_id": "abc123",
            "project_id": "<uuid>"
        }

    Response:
        {"audio_url": "https://..."}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        voice_id = request.data.get("voice_id", "").strip()
        if not voice_id:
            return Response({"detail": "voice_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        text = request.data.get("text", "").strip()

        # If no text provided, look up the project's script
        if not text:
            project_id = request.data.get("project_id", "")
            if not project_id:
                return Response(
                    {"detail": "Provide either 'text' or 'project_id'."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            project = _get_project(project_id, user=request.user)
            if not project:
                return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)

            # Prefer finalized script, fall back to generated
            text = project.finalized_script or project.generated_script
            if not text:
                return Response(
                    {"detail": "Project has no script yet. Generate a script first."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        speed = request.data.get("speed", "1")
        language = request.data.get("language") or None
        locale = request.data.get("locale") or None

        try:
            result = heygen_service.text_to_speech(
                voice_id=voice_id,
                text=text,
                speed=speed,
                language=language,
                locale=locale,
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(result)


class AvatarVoiceView(APIView):
    """
    GET /api/v1/videogen/options/avatars/<avatar_id>/voice/

    Returns the suggested voice for a specific avatar.
    """
    permission_classes = [AllowAny]

    def get(self, request, avatar_id):
        try:
            avatar = CachedAvatar.objects.get(avatar_id=avatar_id, is_active=True)
        except CachedAvatar.DoesNotExist:
            return Response({"detail": "Avatar not found."}, status=404)

        voice = avatar.get_suggested_voice()
        if not voice:
            return Response({"detail": "No suitable voice found."}, status=404)

        return Response(CachedVoiceSerializer(voice).data)


# ═══════════════════════════════════════════════════════════════════════════════
# SCREEN 1 — Create draft project (industry)
#
# POST /projects/create/
# Body: {"industry": "Digital Marketing"}
# Returns: project with id (use this id for all PATCH calls)
# ═══════════════════════════════════════════════════════════════════════════════

class ProjectCreateView(APIView):
    permission_classes = [IsAuthenticated, HasActiveSubscription]

    def post(self, request):
        serializer = ProjectCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        project = VideoProject.objects.create(
            user=request.user,
            industry=serializer.validated_data["industry"],
        )

        return Response(
            VideoProjectSerializer(project, context=_ctx(request)).data,
            status=status.HTTP_201_CREATED,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SCREENS 2, 3, 4 — Update draft project (PATCH any fields)
#
# PATCH /projects/{id}/update/
#
# Screen 2: {"title": "...", "service_description": "..."}
# Screen 3: {"background": "Modern Office"}
# Screen 4: {"avatar_id": "Artur_standing_office_front"}
#
# Can also go back and re-update:
#   {"industry": "Travel & Tourism"}
#   {"title": "New Title"}
#   {"avatar_id": "different_avatar"}
# ═══════════════════════════════════════════════════════════════════════════════

class ProjectUpdateView(APIView):
    permission_classes = [IsAuthenticated, IsProjectOwner]

    def patch(self, request, project_id):
        project = _get_project(project_id)
        if not project:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, project)

        # Only allow updates in draft or script_generated status
        # (user can go back and change things before video generation)
        allowed = [
            VideoProject.StatusChoice.DRAFT,
            VideoProject.StatusChoice.SCRIPT_GENERATED,
            VideoProject.StatusChoice.SCRIPT_FINALIZED,
        ]
        if project.status not in allowed:
            return Response(
                {"detail": f"Cannot update project in '{project.status}' status."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ProjectPatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Update simple fields
        if "industry" in data:
            project.industry = data["industry"]
        if "title" in data:
            project.title = data["title"]
        if "service_description" in data:
            project.service_description = data["service_description"]

        # Background — look up description from DB if name matches
        if "background" in data:
            bg_name = data["background"]
            try:
                bg = Background.objects.get(name=bg_name, is_active=True)
                project.background = bg.description or bg.name
            except Background.DoesNotExist:
                project.background = bg_name  # Custom text, use as-is

        # Avatar — auto-populate name, gender, outfit from CachedAvatar
        if "avatar_id" in data:
            avatar_id = data["avatar_id"]
            project.avatar_id = avatar_id

            try:
                cached = CachedAvatar.objects.get(avatar_id=avatar_id, is_active=True)
                project.avatar_name = cached.avatar_name
                project.avatar_gender = cached.gender
                project.avatar_outfit = cached.outfit_category
                project.avatar_preview_url = cached.preview_image_url
                project.avatar_preview_video_url = cached.preview_video_url
                
                # Auto-select voice if one isn't explicitly provided
                if "voice_id" not in data:
                    project.voice_id = cached.default_voice_id

            except CachedAvatar.DoesNotExist:
                logger.warning(f"Avatar {avatar_id} not in cache")
                project.avatar_name = ""
                project.avatar_gender = ""
                project.avatar_outfit = ""
        
        # Save explicit voice_id if provided (overrides auto-selection)
        if "voice_id" in data:
            project.voice_id = data["voice_id"]

        # If user changes anything after script was generated,
        # reset status back to draft (script is now stale)
        if project.status in (
            VideoProject.StatusChoice.SCRIPT_GENERATED,
            VideoProject.StatusChoice.SCRIPT_FINALIZED,
        ):
            project.status = VideoProject.StatusChoice.DRAFT
            project.generated_script = ""
            project.finalized_script = ""

        project.save()

        return Response(VideoProjectSerializer(project, context=_ctx(request)).data)


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 5 — Generate script (Gemini AI)
# ═══════════════════════════════════════════════════════════════════════════════

class ScriptGenerateView(APIView):
    permission_classes = [IsAuthenticated, HasActiveSubscription, CanGenerateScript]

    def get_throttles(self):
        throttles = super().get_throttles()
        try:
            from core.throttles import ScriptGenerateThrottle
            throttles.append(ScriptGenerateThrottle())
        except ImportError:
            pass
        return throttles

    def post(self, request, project_id):
        project = _get_project(project_id, user=request.user)
        if not project:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)

        # Validate required fields are filled
        missing = []
        if not project.industry:
            missing.append("industry")
        if not project.title:
            missing.append("title")
        if not project.service_description:
            missing.append("service_description")
        if not project.avatar_id:
            missing.append("avatar_id")

        if missing:
            return Response(
                {"detail": f"Please complete these fields first: {', '.join(missing)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        allowed = [
            VideoProject.StatusChoice.DRAFT,
            VideoProject.StatusChoice.SCRIPT_GENERATED,
        ]
        if project.status not in allowed:
            return Response(
                {"detail": "Cannot generate script in current status."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        outfit = project.avatar_outfit or "professional"

        try:
            script = gemini_service.generate_script(
                industry=project.industry,
                service_description=project.service_description,
                avatar_gender=project.avatar_gender or "male",
                avatar_outfit=outfit,
                title=project.title,
                background=project.background,
            )
        except Exception as e:
            return Response(
                {"detail": f"Script generation failed: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        project.generated_script = script
        project.status = VideoProject.StatusChoice.SCRIPT_GENERATED
        project.save()
        request.user.subscription.increment_script_count()

        return Response({
            "project_id": str(project.id),
            "generated_script": script,
            "project": VideoProjectSerializer(project, context=_ctx(request)).data,
        })


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 6 — Finalize script
# ═══════════════════════════════════════════════════════════════════════════════

class ScriptFinalizeView(APIView):
    permission_classes = [IsAuthenticated, HasActiveSubscription, IsProjectOwner]

    def put(self, request, project_id):
        project = _get_project(project_id)
        if not project:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, project)

        not_allowed = [
            VideoProject.StatusChoice.DRAFT,
            VideoProject.StatusChoice.VIDEO_PROCESSING,
            VideoProject.StatusChoice.VIDEO_COMPLETED,
        ]
        if project.status in not_allowed:
            return Response(
                {"detail": f"Cannot finalize script in '{project.status}' status."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ScriptFinalizeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        project.finalized_script = serializer.validated_data["finalized_script"]
        project.status = VideoProject.StatusChoice.SCRIPT_FINALIZED
        project.save()

        return Response(VideoProjectSerializer(project, context=_ctx(request)).data)


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 7 — Generate video (HeyGen Video Agent)
# ═══════════════════════════════════════════════════════════════════════════════

class VideoGenerateView(APIView):
    permission_classes = [IsAuthenticated, HasActiveSubscription, CanGenerateVideo]

    def get_throttles(self):
        throttles = super().get_throttles()
        try:
            from core.throttles import VideoGenerateThrottle
            throttles.append(VideoGenerateThrottle())
        except ImportError:
            pass
        return throttles

    def post(self, request, project_id):
        project = _get_project(project_id, user=request.user)
        if not project:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)

        if project.status != VideoProject.StatusChoice.SCRIPT_FINALIZED:
            return Response(
                {"detail": "Please finalize the script first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not project.avatar_id:
            return Response({"detail": "No avatar selected."}, status=status.HTTP_400_BAD_REQUEST)

        outfit = project.avatar_outfit or "professional"

        try:
            result = heygen_service.generate_video(
                avatar_id=project.avatar_id,
                voice_id=project.voice_id,
                script=project.finalized_script,
                title=project.title,
                industry=project.industry,
                service_description=project.service_description,
                avatar_gender=project.avatar_gender or "male",
                avatar_outfit=outfit,
                background=project.background,
            )
        except Exception as e:
            project.status = VideoProject.StatusChoice.VIDEO_FAILED
            project.video_status_message = str(e)
            project.save()
            return Response(
                {"detail": f"Video generation failed: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        project.heygen_video_id = result["video_id"]
        project.status = VideoProject.StatusChoice.VIDEO_PROCESSING
        project.save()

        # Trigger background monitoring
        from .tasks import monitor_video_status_task
        monitor_video_status_task.delay(str(project.id))

        return Response({
            "project_id": str(project.id),
            "heygen_video_id": result["video_id"],
            "status": "processing",
            "message": "Video generation started. Poll /video-status/ for updates.",
        })


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 8 — Poll video status
# ═══════════════════════════════════════════════════════════════════════════════

class VideoStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = _get_project(project_id, user=request.user)
        if not project:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)

        if not project.heygen_video_id:
            return Response(
                {"detail": "No video generation initiated."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = heygen_service.get_video_status(project.heygen_video_id)
        except Exception as e:
            return Response(
                {"detail": f"Status check failed: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        previous_status = project.status

        if result["status"] == "completed":
            project.status = VideoProject.StatusChoice.VIDEO_COMPLETED
            project.video_url = result["video_url"] or ""

            if previous_status != VideoProject.StatusChoice.VIDEO_COMPLETED:
                if result["video_url"]:
                    try:
                        filename = f"{project.id}.mp4"
                        video_content = heygen_service.download_video(
                            result["video_url"], filename
                        )
                        project.video_file.save(filename, video_content, save=False)
                    except Exception as e:
                        logger.error(f"Failed to save video file: {e}")
                        project.video_status_message = (
                            f"Video completed but file save failed: {e}"
                        )
                request.user.subscription.increment_video_count()

        elif result["status"] == "failed":
            project.status = VideoProject.StatusChoice.VIDEO_FAILED

        project.video_status_message = result.get("message", "")
        project.save()

        return Response({
            "project_id": str(project.id),
            "status": project.status,
            "video_file_url": (
                request.build_absolute_uri(project.video_file.url)
                if project.video_file else None
            ),
            "video_url": project.video_url or None,
            "message": project.video_status_message,
        })


# ═══════════════════════════════════════════════════════════════════════════════
# PROJECT LIST & DETAIL
# ═══════════════════════════════════════════════════════════════════════════════

class ProjectListView(generics.ListAPIView):
    serializer_class = VideoProjectListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = ProjectCursorPagination

    def get_queryset(self):
        return (
            VideoProject.objects
            .filter(user=self.request.user)
            .only(
                "id", "title", "industry", "status",
                "avatar_name", "avatar_outfit",
                "video_file", "created_at",
            )
        )

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx


class ProjectDetailView(APIView):
    permission_classes = [IsAuthenticated, IsProjectOwner]

    def get(self, request, project_id):
        project = _get_project(project_id)
        if not project:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, project)
        return Response(VideoProjectSerializer(project, context=_ctx(request)).data)

    def delete(self, request, project_id):
        project = _get_project(project_id)
        if not project:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, project)
        project.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)