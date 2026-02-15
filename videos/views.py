from rest_framework import generics, permissions, status, views
from rest_framework.response import Response
from .models import VideoProject
from .serializers import VideoProjectSerializer
from .tasks import generate_video_task

class VideoProjectListCreateView(generics.ListCreateAPIView):
    """
    GET: List all video projects for the authenticated user.
    POST: Create a new video project and start generation.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = VideoProjectSerializer

    def get_queryset(self):
        return VideoProject.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        # Auto-populate fields from Avatar ID if provided
        avatar_id = serializer.validated_data.get('avatar_id')
        user_input_outfit = serializer.validated_data.get('avatar_outfit')
        
        if avatar_id:
            from .heygen_service import HeyGenClient
            client = HeyGenClient()
            # Get detailed info for the selected avatar
            selected_avatar = client.get_avatar_details(avatar_id)
            
            if selected_avatar:
                # 1. Force Gender match (Critical for HeyGen)
                api_gender = selected_avatar.get('gender', '').capitalize()
                if api_gender in ['Male', 'Female']:
                    serializer.validated_data['gender'] = api_gender

                # 2. Auto-detect Outfit if not provided
                if not user_input_outfit:
                    name_id = (selected_avatar.get('name', '') + selected_avatar.get('avatar_id', '')).lower()
                    
                    detected_outfit = "Casual"
                    if any(x in name_id for x in ["suit", "office", "formal", "shirt", "business", "professional", "news"]):
                        detected_outfit = "Business"
                    elif any(x in name_id for x in ["doctor", "coat", "medical", "nurse"]):
                        detected_outfit = "Doctor"
                    elif any(x in name_id for x in ["sport", "gym", "fitness", "yoga", "active"]):
                        detected_outfit = "Sport"
                        
                    serializer.validated_data['avatar_outfit'] = detected_outfit
        
        # 3. Save Project
        project = serializer.save(user=self.request.user)
        
        # 4. Trigger the Celery task
        generate_video_task.delay(project.id)

class VideoProjectDetailView(generics.RetrieveAPIView):
    """
    GET: Retrieve details of a specific video project.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = VideoProjectSerializer
    lookup_field = 'id'

    def get_queryset(self):
        return VideoProject.objects.filter(user=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # On-Demand Status Check
        # If it's still processing and has an ID, let's ask HeyGen if it's done yet.
        if instance.status in [VideoProject.Status.PENDING, VideoProject.Status.PROCESSING] and instance.heygen_video_id:
            from .heygen_service import HeyGenClient
            client = HeyGenClient()
            try:
                response = client.check_status(instance.heygen_video_id)
                data = response.get('data', {})
                heygen_status = data.get('status')
                video_url = data.get('video_url') or data.get('url')
                
                # Map HeyGen statuses to our DB statuses
                if heygen_status == 'completed':
                    instance.status = VideoProject.Status.COMPLETED
                    instance.video_url = video_url
                    
                    # Set completion time if not already set
                    from django.utils import timezone
                    if not instance.completed_at:
                        instance.completed_at = timezone.now()
                elif heygen_status == 'failed':
                    instance.status = VideoProject.Status.FAILED
                elif heygen_status in ['processing', 'rendering']:
                    instance.status = VideoProject.Status.PROCESSING
                
                # Edge Case: If it was already completed but missed the timestamp (backfill)
                if instance.status == VideoProject.Status.COMPLETED and not instance.completed_at:
                    from django.utils import timezone
                    instance.completed_at = timezone.now()

                instance.save()
            except Exception as e:
                # If check fails, just ignore and return old status, don't break the view
                pass

        serializer = self.get_serializer(instance)
        return Response(serializer.data)


import json
import os
from django.conf import settings

import random

class AvatarListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Fetch avatars directly from HeyGen API (Real-time)
        client = HeyGenClient()
        raw_avatars = client.get_avatars()
        
        # We need to auto-tag them on the fly since the raw API data doesn't have our "Outfit" tags
        processed_avatars = []
        
        keywords = {
            "Business": ["suit", "office", "formal", "shirt", "business", "professional", "news"],
            "Casual": ["casual", "public", "t-shirt", "hoodie", "sweater", "sofa", "street", "outdoor"],
            "Doctor": ["doctor", "coat", "medical", "nurse"],
            "Sport": ["sport", "gym", "fitness", "yoga", "active"]
        }

        for avatar in raw_avatars:
            if not avatar.get('preview_image_url'):
                continue
                
            name = avatar.get('name', 'Unknown')
            avatar_id = avatar.get('avatar_id')
            gender = avatar.get('gender', 'unknown').capitalize()
            
            # Auto-tagging Outfit
            outfit = "Casual" # Default
            name_lower = name.lower()
            id_lower = avatar_id.lower()
            
            for category, tags in keywords.items():
                if any(tag in name_lower or tag in id_lower for tag in tags):
                    outfit = category
                    break
            
            # Auto-tagging Pose
            pose = "Standing" # Default
            if "sitting" in id_lower or "sofa" in id_lower or "chair" in id_lower:
                pose = "Sitting"
            elif "closeup" in id_lower or "portrait" in id_lower or "head" in id_lower:
                pose = "Closeup"
            
            processed_avatars.append({
                "id": avatar_id,
                "name": name,
                "gender": gender, 
                "outfit": outfit,
                "pose": pose,
                "preview_url": avatar.get('preview_image_url')
            })

        all_avatars = processed_avatars

        # 1. Filter by Gender
        gender_param = request.query_params.get('gender')
        if gender_param:
            all_avatars = [a for a in all_avatars if a.get('gender', '').lower() == gender_param.lower()]

        # 2. Filter by Outfit (Business, Casual, etc.)
        outfit_param = request.query_params.get('outfit')
        if outfit_param:
            all_avatars = [a for a in all_avatars if outfit_param.lower() in a.get('outfit', '').lower()]
            
        # 3. Filter by Pose (Standing, Sitting, Closeup)
        pose_param = request.query_params.get('pose')
        if pose_param:
            all_avatars = [a for a in all_avatars if pose_param.lower() in a.get('pose', '').lower()]
        
        # 4. Randomly select 3 avatars
        random.shuffle(all_avatars)
        selected_avatars = all_avatars[:3]
        
        return Response(selected_avatars)


from .heygen_service import HeyGenClient

class VideoStatusView(views.APIView):
    """
    GET: Force-check the status of a video project from HeyGen Video Agent API
    Link: https://api.heygen.com/v1/video_status.get
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, id):
        try:
            project = VideoProject.objects.get(id=id, user=request.user)
        except VideoProject.DoesNotExist:
            return Response({"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND)

        if not project.heygen_video_id:
            return Response({"error": "Project has no HeyGen Video ID yet"}, status=status.HTTP_400_BAD_REQUEST)

        # Call HeyGen directly
        client = HeyGenClient()
        try:
            response = client.check_status(project.heygen_video_id)
            data = response.get('data', {})
            
            # Update local DB
            heygen_status = data.get('status')
            video_url = data.get('video_url') or data.get('url')
            
            if heygen_status == 'completed':
                project.status = VideoProject.Status.COMPLETED
                project.video_url = video_url
                project.save()
            elif heygen_status == 'failed':
                project.status = VideoProject.Status.FAILED
                project.save()
                
            return Response({
                "id": project.id,
                "heygen_video_id": project.heygen_video_id,
                "status": project.status, # Our mapped status
                "heygen_status": heygen_status, # Raw status
                "video_url": project.video_url,
                "error": data.get('error')
            })

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)
