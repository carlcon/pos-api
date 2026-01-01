from django.urls import path
from . import views

urlpatterns = [
    # Notifications
    path('', views.NotificationListView.as_view(), name='notification-list'),
    path('unread-count/', views.notification_unread_count, name='notification-unread-count'),
    path('<int:pk>/read/', views.mark_notification_read, name='notification-mark-read'),
    path('mark-all-read/', views.mark_all_notifications_read, name='notification-mark-all-read'),
    path('<int:pk>/', views.delete_notification, name='notification-delete'),
    
    # Export Jobs
    path('exports/', views.ExportJobListView.as_view(), name='export-list'),
    path('exports/create/', views.create_export_job, name='export-create'),
    path('exports/<int:pk>/status/', views.export_job_status, name='export-status'),
    path('exports/<int:pk>/download/', views.download_export, name='export-download'),
]
