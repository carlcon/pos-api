from django.db import models
from django.conf import settings


class Notification(models.Model):
    """
    In-app notification model for user notifications.
    Supports different notification types with optional JSON data.
    """
    
    class Type(models.TextChoices):
        STORE_ADMIN_TRANSFER = 'STORE_ADMIN_TRANSFER', 'Store Admin Transfer'
        LOW_STOCK_ALERT = 'LOW_STOCK_ALERT', 'Low Stock Alert'
        OUT_OF_STOCK_ALERT = 'OUT_OF_STOCK_ALERT', 'Out of Stock Alert'
        EXPORT_COMPLETE = 'EXPORT_COMPLETE', 'Export Complete'
        STORE_DEACTIVATED = 'STORE_DEACTIVATED', 'Store Deactivated'
        STORE_ACTIVATED = 'STORE_ACTIVATED', 'Store Activated'
        PASSWORD_RESET = 'PASSWORD_RESET', 'Password Reset'
        GENERAL = 'GENERAL', 'General'
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    type = models.CharField(
        max_length=30,
        choices=Type.choices,
        default=Type.GENERAL
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    data = models.JSONField(
        blank=True,
        null=True,
        help_text='Optional JSON data for notification context'
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
            models.Index(fields=['user', 'type']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
    def mark_as_read(self):
        """Mark notification as read."""
        from django.utils import timezone
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class ExportJob(models.Model):
    """
    Track background export jobs.
    """
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PROCESSING = 'PROCESSING', 'Processing'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'
    
    class ExportType(models.TextChoices):
        SALES_CSV = 'SALES_CSV', 'Sales CSV'
        SALES_EXCEL = 'SALES_EXCEL', 'Sales Excel'
        SALES_PDF = 'SALES_PDF', 'Sales PDF'
        PRODUCTS_CSV = 'PRODUCTS_CSV', 'Products CSV'
        PRODUCTS_EXCEL = 'PRODUCTS_EXCEL', 'Products Excel'
        STOCK_CSV = 'STOCK_CSV', 'Stock CSV'
        STOCK_EXCEL = 'STOCK_EXCEL', 'Stock Excel'
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='export_jobs'
    )
    export_type = models.CharField(
        max_length=20,
        choices=ExportType.choices
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    filters = models.JSONField(
        blank=True,
        null=True,
        help_text='Filters applied to the export'
    )
    file_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text='Path to the generated file'
    )
    error_message = models.TextField(
        blank=True,
        null=True,
        help_text='Error message if export failed'
    )
    progress = models.IntegerField(
        default=0,
        help_text='Progress percentage (0-100)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'export_jobs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.export_type} - {self.status}"
