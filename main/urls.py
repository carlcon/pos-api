"""
URL configuration for main project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


# Simple health check view - no database required
def health_check(request):
    """Health check endpoint for container orchestration.
    Returns 200 OK without database queries for fast response.
    """
    return JsonResponse({
        'status': 'healthy',
        'service': 'pos-api'
    })


urlpatterns = [
    # Health check endpoint (no auth required, no DB queries)
    path('api/health/', health_check, name='health-check'),
    
    path('admin/', admin.site.urls),
    
    # OAuth2
    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    
    # API endpoints
    path('api/auth/', include('users.urls')),
    path('api/inventory/', include('inventory.urls')),
    path('api/sales/', include('sales.urls')),
    path('api/stock/', include('stock.urls')),
    path('api/dashboard/', include('dashboard.urls')),
    path('api/expenses/', include('expenses.urls')),
    path('api/notifications/', include('notifications.urls')),
    path('api/', include('stores.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
