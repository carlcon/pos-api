from rest_framework import serializers
from .models import Notification, ExportJob


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model."""
    
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'type', 'type_display', 'title', 'message', 
            'data', 'is_read', 'created_at', 'read_at'
        ]
        read_only_fields = ['id', 'type', 'title', 'message', 'data', 'created_at']


class ExportJobSerializer(serializers.ModelSerializer):
    """Serializer for ExportJob model."""
    
    export_type_display = serializers.CharField(source='get_export_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    download_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ExportJob
        fields = [
            'id', 'export_type', 'export_type_display', 'status', 'status_display',
            'filters', 'progress', 'error_message', 'download_url',
            'created_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'status', 'progress', 'error_message', 
            'download_url', 'created_at', 'completed_at'
        ]
    
    def get_download_url(self, obj):
        """Generate download URL if file is ready."""
        if obj.status == ExportJob.Status.COMPLETED and obj.file_path:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(f'/api/exports/{obj.id}/download/')
        return None


class ExportJobCreateSerializer(serializers.Serializer):
    """Serializer for creating export jobs."""
    
    export_type = serializers.ChoiceField(choices=ExportJob.ExportType.choices)
    filters = serializers.JSONField(required=False, allow_null=True)
