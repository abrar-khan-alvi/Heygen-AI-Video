from rest_framework import serializers
from .models import VideoProject

class VideoProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoProject
        fields = [
            'id',
            'title',
            'industry',
            'service_description',
            'gender',
            'gender',
            'background_type',
            'avatar_outfit',
            'avatar_id',
            'heygen_video_id',
            'constructed_prompt',
            'status',
            'video_url',
            'created_at',
            'completed_at'
        ]
        read_only_fields = ['id', 'status', 'video_url', 'created_at', 'completed_at', 'heygen_video_id', 'constructed_prompt']
        extra_kwargs = {
            'gender': {'required': False, 'allow_blank': True},
            'avatar_outfit': {'required': False, 'allow_blank': True},
            'background_type': {'required': False, 'allow_blank': True},
        }

    def create(self, validated_data):
        # We can auto-generate a title here if we want, or model save() handles it.
        return super().create(validated_data)
