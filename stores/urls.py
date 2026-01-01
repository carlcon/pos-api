from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import StoreViewSet, preview_receipt

app_name = 'stores'

router = DefaultRouter()
router.register(r'stores', StoreViewSet, basename='store')

urlpatterns = [
    path('stores/<int:store_id>/preview-receipt/', preview_receipt, name='preview-receipt'),
] + router.urls
