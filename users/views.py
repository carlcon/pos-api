from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from oauth2_provider.models import Application, AccessToken, RefreshToken
from oauth2_provider.settings import oauth2_settings
from oauthlib.common import generate_token
from datetime import timedelta
from django.utils import timezone
from .models import User, Partner
from .serializers import (
    UserSerializer, UserCreateSerializer, UserUpdateSerializer, ChangePasswordSerializer,
    PartnerSerializer
)
from .permissions import IsAdmin, IsSuperAdmin, IsAdminOrSuperAdmin
from stores.models import Store
from stores.serializers import StoreSerializer


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    OAuth2 login endpoint that returns access and refresh tokens.
    Checks store status for STORE_ADMIN/CASHIER users.
    """
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response(
            {'error': 'Username and password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = authenticate(username=username, password=password)
    
    if user is None:
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    if not user.is_active or not user.is_active_employee:
        return Response(
            {'error': 'User account is disabled'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Check store status for store-level users
    if user.is_store_level_user and user.assigned_store:
        if not user.assigned_store.is_active:
            return Response(
                {'error': 'Your store is currently inactive. Please contact your administrator.'},
                status=status.HTTP_403_FORBIDDEN
            )
    
    # Get or create OAuth2 application
    application = Application.objects.filter(name='pos-frontend').first()
    if not application:
        application = Application.objects.create(
            name='pos-frontend',
            client_type=Application.CLIENT_PUBLIC,
            authorization_grant_type=Application.GRANT_PASSWORD,
        )
    
    # Create access token
    expires = timezone.now() + timedelta(
        seconds=oauth2_settings.ACCESS_TOKEN_EXPIRE_SECONDS
    )
    access_token = AccessToken.objects.create(
        user=user,
        application=application,
        token=generate_token(),
        expires=expires,
        scope='read write'
    )
    
    # Create refresh token
    refresh_token = RefreshToken.objects.create(
        user=user,
        application=application,
        token=generate_token(),
        access_token=access_token
    )
    
    user_data = UserSerializer(user).data
    
    return Response({
        'access_token': access_token.token,
        'refresh_token': refresh_token.token,
        'expires_in': oauth2_settings.ACCESS_TOKEN_EXPIRE_SECONDS,
        'token_type': 'Bearer',
        'user': user_data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Logout by revoking tokens"""
    try:
        # Get tokens from authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            token_string = auth_header.split(' ')[1]
            access_token = AccessToken.objects.get(token=token_string)
            
            # Delete refresh token
            RefreshToken.objects.filter(access_token=access_token).delete()
            
            # Delete access token
            access_token.delete()
            
            return Response({'message': 'Successfully logged out'})
    except AccessToken.DoesNotExist:
        pass
    
    return Response({'message': 'Logged out'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user_view(request):
    """Get current authenticated user details"""
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


class UserListCreateView(generics.ListCreateAPIView):
    """List all users or create new user (Admin only)"""
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UserCreateSerializer
        return UserSerializer
    
    def get_queryset(self):
        """
        Filter users based on who is requesting:
        - Super Admin: sees all users
        - Partner Admin: sees only users in their partner
        """
        queryset = super().get_queryset()
        user = self.request.user
        
        if user.is_super_admin:
            # Super admin can see all users, optionally filter by partner
            partner_id = self.request.query_params.get('partner', None)
            if partner_id:
                queryset = queryset.filter(partner_id=partner_id)
        else:
            # Partner admin can only see users in their partner
            queryset = queryset.filter(partner=user.partner)
        
        return queryset
    
    def perform_create(self, serializer):
        """
        Auto-assign partner on user creation:
        - Super Admin: can specify partner_id, or create super admins
        - Partner Admin: new users auto-assigned to their partner
        """
        user = self.request.user
        
        if user.is_super_admin:
            # Super admin can create users for any partner
            serializer.save()
        else:
            # Partner admin creates users in their own partner
            serializer.save(partner=user.partner, is_super_admin=False)


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a user (Admin only)"""
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return UserUpdateSerializer
        return UserSerializer
    
    def get_queryset(self):
        """Filter users to only those the current user can manage."""
        queryset = super().get_queryset()
        user = self.request.user
        
        if user.is_super_admin:
            return queryset
        else:
            # Partner admin can only manage users in their partner
            return queryset.filter(partner=user.partner)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password_view(request):
    """Change user password"""
    serializer = ChangePasswordSerializer(data=request.data)
    
    if serializer.is_valid():
        user = request.user
        
        # Check old password
        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {'error': 'Old password is incorrect'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Set new password
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({'message': 'Password changed successfully'})
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============== Partner Views ==============

class PartnerListCreateView(generics.ListCreateAPIView):
    """List all partners or create new partner (Super Admin only)"""
    queryset = Partner.objects.all()
    serializer_class = PartnerSerializer
    permission_classes = [IsAuthenticated, IsSuperAdmin]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Search by name or code
        search = self.request.query_params.get('search', None)
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(code__icontains=search)
            )
        
        return queryset


class PartnerDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a partner (Super Admin only)"""
    queryset = Partner.objects.all()
    serializer_class = PartnerSerializer
    permission_classes = [IsAuthenticated, IsSuperAdmin]


# ============== Impersonation Views ==============

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsSuperAdmin])
def impersonate_partner(request, partner_id):
    """
    Super Admin impersonates a partner by getting a partner-scoped token.
    Returns a new access token that is scoped to the specified partner.
    The original token should be stored client-side to restore later.
    """
    partner = get_object_or_404(Partner, id=partner_id)
    
    if not partner.is_active:
        return Response(
            {'error': 'Cannot impersonate inactive partner'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get or create OAuth2 application
    application = Application.objects.filter(name='pos-frontend').first()
    if not application:
        return Response(
            {'error': 'OAuth application not found'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Create a new access token with partner scope stored in scope field
    expires = timezone.now() + timedelta(
        seconds=oauth2_settings.ACCESS_TOKEN_EXPIRE_SECONDS
    )
    
    # Create impersonation token - scope contains partner info
    impersonation_token = AccessToken.objects.create(
        user=request.user,
        application=application,
        token=generate_token(),
        expires=expires,
        scope=f'read write impersonating:{partner.id}'
    )
    
    # Create refresh token for impersonation session
    refresh_token = RefreshToken.objects.create(
        user=request.user,
        application=application,
        token=generate_token(),
        access_token=impersonation_token
    )
    
    return Response({
        'access_token': impersonation_token.token,
        'refresh_token': refresh_token.token,
        'expires_in': oauth2_settings.ACCESS_TOKEN_EXPIRE_SECONDS,
        'token_type': 'Bearer',
        'impersonating': PartnerSerializer(partner).data,
        'message': f'Now viewing as {partner.name}'
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def exit_impersonation(request):
    """
    Exit impersonation mode by revoking the impersonation token.
    Client should switch back to the original stored token.
    """
    try:
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            token_string = auth_header.split(' ')[1]
            access_token = AccessToken.objects.get(token=token_string)
            
            # Check if this is an impersonation token
            if 'impersonating:' in access_token.scope:
                # Delete the impersonation token
                RefreshToken.objects.filter(access_token=access_token).delete()
                access_token.delete()
                return Response({'message': 'Exited impersonation mode'})
            else:
                return Response(
                    {'error': 'Not in impersonation mode'},
                    status=status.HTTP_400_BAD_REQUEST
                )
    except AccessToken.DoesNotExist:
        pass
    
    return Response(
        {'error': 'Invalid token'},
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_impersonation_status(request):
    """
    Check if current token is an impersonation token and return partner/store info.
    """
    result = {
        'is_impersonating_partner': False,
        'partner': None,
        'is_impersonating_store': False,
        'store': None,
    }
    
    try:
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            token_string = auth_header.split(' ')[1]
            access_token = AccessToken.objects.get(token=token_string)
            
            # Check for partner impersonation
            if 'impersonating:' in access_token.scope:
                scope_parts = access_token.scope.split()
                for part in scope_parts:
                    if part.startswith('impersonating:'):
                        partner_id = int(part.split(':')[1])
                        partner = Partner.objects.get(id=partner_id)
                        result['is_impersonating_partner'] = True
                        result['partner'] = PartnerSerializer(partner).data
                        break
            
            # Check for store impersonation
            if 'impersonating_store:' in access_token.scope:
                scope_parts = access_token.scope.split()
                for part in scope_parts:
                    if part.startswith('impersonating_store:'):
                        store_id = int(part.split(':')[1])
                        store = Store.objects.get(id=store_id)
                        result['is_impersonating_store'] = True
                        result['store'] = StoreSerializer(store).data
                        break
    except (AccessToken.DoesNotExist, Partner.DoesNotExist, Store.DoesNotExist, ValueError):
        pass
    
    return Response(result)


# ============== Store Impersonation Views ==============

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminOrSuperAdmin])
def impersonate_store(request, partner_id, store_id):
    """
    Partner Admin or Super Admin impersonates a store.
    Creates a new token with store scope.
    
    For Super Admin: must already be impersonating the partner.
    For Partner Admin: can directly impersonate stores in their partner.
    """
    user = request.user
    
    # Get the store
    store = get_object_or_404(Store, id=store_id, partner_id=partner_id)
    
    if not store.is_active:
        return Response(
            {'error': 'Cannot impersonate inactive store'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Verify access
    if user.is_super_admin:
        # Super admin must be impersonating the partner
        from users.mixins import get_partner_from_request
        effective_partner = get_partner_from_request(request)
        if not effective_partner or effective_partner.id != partner_id:
            return Response(
                {'error': 'Must impersonate partner before impersonating store'},
                status=status.HTTP_403_FORBIDDEN
            )
    elif user.is_admin:
        # Partner admin can only impersonate stores in their partner
        if user.partner_id != partner_id:
            return Response(
                {'error': 'Cannot impersonate store from different partner'},
                status=status.HTTP_403_FORBIDDEN
            )
    else:
        return Response(
            {'error': 'Insufficient permissions'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get OAuth2 application
    application = Application.objects.filter(name='pos-frontend').first()
    if not application:
        return Response(
            {'error': 'OAuth application not found'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Build scope - preserve partner impersonation if exists
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    current_scope = 'read write'
    
    if auth_header.startswith('Bearer '):
        token_string = auth_header.split(' ')[1]
        try:
            current_token = AccessToken.objects.get(token=token_string)
            if 'impersonating:' in current_token.scope:
                # Preserve partner impersonation
                for part in current_token.scope.split():
                    if part.startswith('impersonating:'):
                        current_scope += f' {part}'
                        break
        except AccessToken.DoesNotExist:
            pass
    
    # Add store impersonation to scope
    new_scope = f'{current_scope} impersonating_store:{store.id}'
    
    # Create store impersonation token with separate expiry
    expires = timezone.now() + timedelta(
        seconds=oauth2_settings.ACCESS_TOKEN_EXPIRE_SECONDS
    )
    
    store_token = AccessToken.objects.create(
        user=user,
        application=application,
        token=generate_token(),
        expires=expires,
        scope=new_scope
    )
    
    # Create refresh token
    refresh_token = RefreshToken.objects.create(
        user=user,
        application=application,
        token=generate_token(),
        access_token=store_token
    )
    
    return Response({
        'access_token': store_token.token,
        'refresh_token': refresh_token.token,
        'expires_in': oauth2_settings.ACCESS_TOKEN_EXPIRE_SECONDS,
        'token_type': 'Bearer',
        'impersonating_store': StoreSerializer(store).data,
        'message': f'Now viewing as store: {store.name}'
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def exit_store_impersonation(request):
    """
    Exit store impersonation mode.
    Keeps partner impersonation active if applicable.
    """
    try:
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            token_string = auth_header.split(' ')[1]
            access_token = AccessToken.objects.get(token=token_string)
            
            # Check if this is a store impersonation token
            if 'impersonating_store:' not in access_token.scope:
                return Response(
                    {'error': 'Not in store impersonation mode'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if also impersonating partner
            has_partner_impersonation = 'impersonating:' in access_token.scope
            
            if has_partner_impersonation:
                # Create new token with only partner impersonation
                application = access_token.application
                expires = timezone.now() + timedelta(
                    seconds=oauth2_settings.ACCESS_TOKEN_EXPIRE_SECONDS
                )
                
                # Extract partner impersonation from scope
                partner_scope = 'read write'
                for part in access_token.scope.split():
                    if part.startswith('impersonating:'):
                        partner_scope += f' {part}'
                        break
                
                # Create new partner-only impersonation token
                new_token = AccessToken.objects.create(
                    user=access_token.user,
                    application=application,
                    token=generate_token(),
                    expires=expires,
                    scope=partner_scope
                )
                
                new_refresh = RefreshToken.objects.create(
                    user=access_token.user,
                    application=application,
                    token=generate_token(),
                    access_token=new_token
                )
                
                # Delete the store impersonation token
                RefreshToken.objects.filter(access_token=access_token).delete()
                access_token.delete()
                
                return Response({
                    'message': 'Exited store impersonation mode',
                    'access_token': new_token.token,
                    'refresh_token': new_refresh.token,
                    'expires_in': oauth2_settings.ACCESS_TOKEN_EXPIRE_SECONDS,
                    'token_type': 'Bearer',
                })
            else:
                # Just delete the store impersonation token
                RefreshToken.objects.filter(access_token=access_token).delete()
                access_token.delete()
                return Response({'message': 'Exited store impersonation mode'})
                
    except AccessToken.DoesNotExist:
        pass
    
    return Response(
        {'error': 'Invalid token'},
        status=status.HTTP_400_BAD_REQUEST
    )
