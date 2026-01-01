from django.contrib import admin
from .models import Notification, ExportJob


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'type', 'title', 'is_read', 'created_at']
    list_filter = ['type', 'is_read', 'created_at']
    search_fields = ['user__username', 'title', 'message']
    readonly_fields = ['created_at', 'read_at']
    ordering = ['-created_at']


@admin.register(ExportJob)
class ExportJobAdmin(admin.ModelAdmin):
    list_display = ['user', 'export_type', 'status', 'progress', 'created_at', 'completed_at']
    list_filter = ['export_type', 'status', 'created_at']
    search_fields = ['user__username']
    readonly_fields = ['created_at', 'completed_at']
    ordering = ['-created_at']
