from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, filters, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from users.models import User
from users.permissions import IsAdminOrSuperAdmin, CanManageStores
from users.mixins import PartnerFilterViewSetMixin, get_partner_from_request
from .models import Store
from .serializers import (
    StoreSerializer, StoreCreateUpdateSerializer,
    StoreUserSerializer, StoreUserCreateSerializer, 
    StoreUserUpdateSerializer, StoreUserPasswordResetSerializer
)

# Shortcut for User.Role
Role = User.Role


class StoreViewSet(PartnerFilterViewSetMixin, viewsets.ModelViewSet):
    """
    ViewSet for Store management.
    Partner Admins can manage stores in their partner.
    Super Admins can manage stores when impersonating a partner.
    """
    queryset = Store.objects.all()
    permission_classes = [IsAuthenticated, CanManageStores]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'code', 'address', 'contact_email', 'contact_phone']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return StoreCreateUpdateSerializer
        return StoreSerializer
    
    def get_queryset(self):
        """Annotate queryset with user counts"""
        qs = super().get_queryset()
        return qs.annotate(
            admin_count=Count('assigned_users', filter=Q(assigned_users__role=Role.STORE_ADMIN)),
            cashier_count=Count('assigned_users', filter=Q(assigned_users__role=Role.CASHIER))
        )

    @transaction.atomic
    def perform_create(self, serializer):
        """
        Create store with auto-generated Store Admin user.
        Username pattern: {partner_username}_store{N}_admin
        Default password: Admin1234@
        """
        partner = get_partner_from_request(self.request)
        if not partner:
            partner = self.request.user.partner
        
        store = serializer.save(partner=partner)
        
        # Generate store admin username
        # Get partner admin username
        partner_admin = User.objects.filter(
            partner=partner, 
            role=Role.ADMIN
        ).first()
        
        partner_username = partner_admin.username if partner_admin else partner.code.lower()
        
        # Count existing stores for numbering
        store_count = Store.objects.filter(partner=partner).count()
        
        admin_username = f"{partner_username}_store{store_count}_admin"
        
        # Ensure unique username
        base_username = admin_username
        counter = 1
        while User.objects.filter(username=admin_username).exists():
            admin_username = f"{base_username}_{counter}"
            counter += 1
        
        # Create Store Admin user
        store_admin = User.objects.create_user(
            username=admin_username,
            password='Admin1234@',
            role=Role.STORE_ADMIN,
            partner=partner,
            assigned_store=store,
            email=store.contact_email or '',
            first_name='Store',
            last_name='Admin',
        )
        
        # Store the created admin info in instance for response
        store._created_admin = store_admin
    
    def create(self, request, *args, **kwargs):
        """Override to include created admin info in response"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Re-fetch with annotations
        store = self.get_queryset().get(pk=serializer.instance.pk)
        response_serializer = StoreSerializer(store)
        data = response_serializer.data
        
        # Add created admin info
        if hasattr(serializer.instance, '_created_admin'):
            admin = serializer.instance._created_admin
            data['created_admin'] = {
                'id': admin.id,
                'username': admin.username,
                'default_password': 'Admin1234@',
                'message': 'Store Admin user created. Please change the default password.'
            }
        
        headers = self.get_success_headers(data)
        return Response(data, status=status.HTTP_201_CREATED, headers=headers)
    
    def retrieve(self, request, *args, **kwargs):
        """Override to ensure annotations are present"""
        instance = self.get_object()
        # Re-fetch with annotations
        instance = self.get_queryset().get(pk=instance.pk)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def update(self, request, *args, **kwargs):
        """Override to ensure annotations are present in response"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Re-fetch with annotations
        instance = self.get_queryset().get(pk=instance.pk)
        response_serializer = StoreSerializer(instance)
        return Response(response_serializer.data)

    # ============== Store User Management Actions ==============
    
    @action(detail=True, methods=['get'], url_path='users')
    def list_users(self, request, pk=None):
        """
        List all users (Store Admins and Cashiers) assigned to this store.
        """
        store = self.get_object()
        users = User.objects.filter(
            assigned_store=store,
            role__in=[Role.STORE_ADMIN, Role.CASHIER]
        ).order_by('role', 'username')
        
        serializer = StoreUserSerializer(users, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='users/admin')
    def create_admin(self, request, pk=None):
        """
        Create additional Store Admin user for this store.
        """
        store = self.get_object()
        serializer = StoreUserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Generate username
        partner = store.partner
        partner_admin = User.objects.filter(partner=partner, role=Role.ADMIN).first()
        partner_username = partner_admin.username if partner_admin else partner.code.lower()
        
        admin_count = User.objects.filter(
            assigned_store=store, 
            role=Role.STORE_ADMIN
        ).count()
        
        admin_username = f"{partner_username}_store{store.id}_admin{admin_count + 1}"
        
        # Ensure unique
        base_username = admin_username
        counter = 1
        while User.objects.filter(username=admin_username).exists():
            admin_username = f"{base_username}_{counter}"
            counter += 1
        
        user = User.objects.create_user(
            username=admin_username,
            password=serializer.validated_data.get('password', 'Admin1234@'),
            role=Role.STORE_ADMIN,
            partner=partner,
            assigned_store=store,
            email=serializer.validated_data.get('email', ''),
            first_name=serializer.validated_data.get('first_name', ''),
            last_name=serializer.validated_data.get('last_name', ''),
            sms_phone=serializer.validated_data.get('sms_phone'),
            is_active=serializer.validated_data.get('is_active', True),
        )
        
        response_data = StoreUserSerializer(user).data
        response_data['default_password'] = serializer.validated_data.get('password', 'Admin1234@')
        
        return Response(response_data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'], url_path='users/cashier')
    def create_cashier(self, request, pk=None):
        """
        Create Cashier user for this store.
        """
        store = self.get_object()
        serializer = StoreUserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Generate username
        partner = store.partner
        partner_admin = User.objects.filter(partner=partner, role=Role.ADMIN).first()
        partner_username = partner_admin.username if partner_admin else partner.code.lower()
        
        cashier_count = User.objects.filter(
            assigned_store=store, 
            role=Role.CASHIER
        ).count()
        
        cashier_username = f"{partner_username}_store{store.id}_cashier{cashier_count + 1}"
        
        # Ensure unique
        base_username = cashier_username
        counter = 1
        while User.objects.filter(username=cashier_username).exists():
            cashier_username = f"{base_username}_{counter}"
            counter += 1
        
        user = User.objects.create_user(
            username=cashier_username,
            password=serializer.validated_data.get('password', 'Admin1234@'),
            role=Role.CASHIER,
            partner=partner,
            assigned_store=store,
            email=serializer.validated_data.get('email', ''),
            first_name=serializer.validated_data.get('first_name', ''),
            last_name=serializer.validated_data.get('last_name', ''),
            sms_phone=serializer.validated_data.get('sms_phone'),
            is_active=serializer.validated_data.get('is_active', True),
        )
        
        response_data = StoreUserSerializer(user).data
        response_data['default_password'] = serializer.validated_data.get('password', 'Admin1234@')
        
        return Response(response_data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['patch'], url_path='users/(?P<user_id>[^/.]+)')
    def update_user(self, request, pk=None, user_id=None):
        """
        Update a Store Admin or Cashier user.
        """
        store = self.get_object()
        user = get_object_or_404(
            User, 
            id=user_id, 
            assigned_store=store,
            role__in=[Role.STORE_ADMIN, Role.CASHIER]
        )
        
        serializer = StoreUserUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        for field, value in serializer.validated_data.items():
            setattr(user, field, value)
        user.save()
        
        return Response(StoreUserSerializer(user).data)
    
    @action(detail=True, methods=['delete'], url_path='users/(?P<user_id>[^/.]+)/delete')
    def delete_user(self, request, pk=None, user_id=None):
        """
        Delete (deactivate) a Store Admin or Cashier user.
        Cannot delete the last Store Admin.
        """
        store = self.get_object()
        user = get_object_or_404(
            User, 
            id=user_id, 
            assigned_store=store,
            role__in=[Role.STORE_ADMIN, Role.CASHIER]
        )
        
        # Check if this is the last store admin
        if user.role == Role.STORE_ADMIN:
            admin_count = User.objects.filter(
                assigned_store=store,
                role=Role.STORE_ADMIN,
                is_active=True
            ).exclude(id=user.id).count()
            
            if admin_count == 0:
                return Response(
                    {'error': 'Cannot delete the last Store Admin. Create another admin first.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Soft delete - just deactivate
        user.is_active = False
        user.save()
        
        return Response({'message': f'User {user.username} has been deactivated.'})
    
    @action(detail=True, methods=['post'], url_path='users/(?P<user_id>[^/.]+)/reset-password')
    def reset_user_password(self, request, pk=None, user_id=None):
        """
        Reset password for a Store Admin or Cashier user.
        """
        store = self.get_object()
        user = get_object_or_404(
            User, 
            id=user_id, 
            assigned_store=store,
            role__in=[Role.STORE_ADMIN, Role.CASHIER]
        )
        
        serializer = StoreUserPasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({'message': f'Password reset successfully for {user.username}.'})


# ============== Receipt Preview ==============

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def preview_receipt(request, store_id):
    """
    Preview receipt with sample data using store's template.
    """
    partner = get_partner_from_request(request)
    if not partner:
        partner = request.user.partner
    
    store = get_object_or_404(Store, id=store_id, partner=partner)
    
    # Sample data for preview
    sample_data = {
        'store_name': store.name,
        'store_address': store.address or '123 Sample Street',
        'store_phone': store.contact_phone or '(555) 123-4567',
        'receipt_number': 'RCP-2024-00001',
        'date': 'Jan 15, 2024 2:30 PM',
        'cashier': 'Sample Cashier',
        'items': [
            {'name': 'Sample Product 1', 'qty': 2, 'price': 10.00, 'total': 20.00},
            {'name': 'Sample Product 2', 'qty': 1, 'price': 25.50, 'total': 25.50},
            {'name': 'Sample Product 3', 'qty': 3, 'price': 5.00, 'total': 15.00},
        ],
        'subtotal': 60.50,
        'tax': 4.84,
        'discount': 0.00,
        'total': 65.34,
        'payment_method': 'Cash',
        'amount_paid': 70.00,
        'change': 4.66,
    }
    
    receipt_html = store.render_receipt(sample_data)
    
    return Response({
        'html': receipt_html,
        'template': store.receipt_template,
    })
