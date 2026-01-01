from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.http import FileResponse
from django.utils import timezone
import os

from .models import Notification, ExportJob
from .serializers import (
    NotificationSerializer, 
    ExportJobSerializer, 
    ExportJobCreateSerializer
)
from users.permissions import CanViewNotifications


class NotificationPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class NotificationListView(generics.ListAPIView):
    """
    List notifications for the current user.
    Supports filtering by type and read status.
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated, CanViewNotifications]
    pagination_class = NotificationPagination
    
    def get_queryset(self):
        queryset = Notification.objects.filter(user=self.request.user)
        
        # Filter by type
        notification_type = self.request.query_params.get('type')
        if notification_type:
            queryset = queryset.filter(type=notification_type)
        
        # Filter by read status
        is_read = self.request.query_params.get('is_read')
        if is_read is not None:
            queryset = queryset.filter(is_read=is_read.lower() == 'true')
        
        return queryset


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_unread_count(request):
    """Get count of unread notifications."""
    count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()
    return Response({'unread_count': count})


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, pk):
    """Mark a notification as read."""
    notification = get_object_or_404(
        Notification,
        pk=pk,
        user=request.user
    )
    notification.mark_as_read()
    return Response(NotificationSerializer(notification).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_notifications_read(request):
    """Mark all notifications as read for the current user."""
    updated_count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).update(
        is_read=True,
        read_at=timezone.now()
    )
    return Response({
        'message': f'Marked {updated_count} notifications as read',
        'updated_count': updated_count
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_notification(request, pk):
    """Delete a notification."""
    notification = get_object_or_404(
        Notification,
        pk=pk,
        user=request.user
    )
    notification.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ============== Export Job Views ==============

class ExportJobListView(generics.ListAPIView):
    """List export jobs for the current user."""
    serializer_class = ExportJobSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = NotificationPagination
    
    def get_queryset(self):
        return ExportJob.objects.filter(user=self.request.user)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_export_job(request):
    """
    Create a new export job.
    The actual export will be processed by Celery.
    """
    serializer = ExportJobCreateSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    export_type = serializer.validated_data['export_type']
    filters = serializer.validated_data.get('filters')
    
    # Create the export job
    job = ExportJob.objects.create(
        user=request.user,
        export_type=export_type,
        filters=filters,
        status=ExportJob.Status.PENDING
    )
    
    # Trigger Celery task
    try:
        from notifications.tasks import process_export_job
        process_export_job.delay(job.id)
    except Exception as e:
        # Celery might not be configured yet
        job.status = ExportJob.Status.FAILED
        job.error_message = f"Failed to start export: {str(e)}"
        job.save()
    
    return Response(
        ExportJobSerializer(job, context={'request': request}).data,
        status=status.HTTP_201_CREATED
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_job_status(request, pk):
    """Get the status of an export job."""
    job = get_object_or_404(
        ExportJob,
        pk=pk,
        user=request.user
    )
    return Response(ExportJobSerializer(job, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_export(request, pk):
    """Download a completed export file."""
    job = get_object_or_404(
        ExportJob,
        pk=pk,
        user=request.user
    )
    
    if job.status != ExportJob.Status.COMPLETED:
        return Response(
            {'error': 'Export is not ready yet'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not job.file_path or not os.path.exists(job.file_path):
        return Response(
            {'error': 'Export file not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Determine content type
    content_types = {
        ExportJob.ExportType.SALES_CSV: 'text/csv',
        ExportJob.ExportType.SALES_EXCEL: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        ExportJob.ExportType.SALES_PDF: 'application/pdf',
        ExportJob.ExportType.PRODUCTS_CSV: 'text/csv',
        ExportJob.ExportType.PRODUCTS_EXCEL: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        ExportJob.ExportType.STOCK_CSV: 'text/csv',
        ExportJob.ExportType.STOCK_EXCEL: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    }
    
    content_type = content_types.get(job.export_type, 'application/octet-stream')
    filename = os.path.basename(job.file_path)
    
    response = FileResponse(
        open(job.file_path, 'rb'),
        content_type=content_type
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
