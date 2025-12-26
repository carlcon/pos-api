from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from users.permissions import IsAdminOrSuperAdmin
from users.mixins import PartnerFilterViewSetMixin
from .models import Store
from .serializers import StoreSerializer, StoreCreateUpdateSerializer


class StoreViewSet(PartnerFilterViewSetMixin, viewsets.ModelViewSet):
    queryset = Store.objects.all()
    permission_classes = [IsAuthenticated, IsAdminOrSuperAdmin]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'code', 'address', 'contact_email', 'contact_phone']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return StoreCreateUpdateSerializer
        return StoreSerializer
