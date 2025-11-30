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
from .permissions import IsAdmin, IsSuperAdmin


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    OAuth2 login endpoint that returns access and refresh tokens
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
    
    # Get or create OAuth2 application
    try:
        application = Application.objects.get(name='pos-frontend')
    except Application.DoesNotExist:
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
    try:
        application = Application.objects.get(name='pos-frontend')
    except Application.DoesNotExist:
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
    Check if current token is an impersonation token and return partner info.
    """
    try:
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            token_string = auth_header.split(' ')[1]
            access_token = AccessToken.objects.get(token=token_string)
            
            # Check if this is an impersonation token
            if 'impersonating:' in access_token.scope:
                # Extract partner ID from scope
                scope_parts = access_token.scope.split()
                for part in scope_parts:
                    if part.startswith('impersonating:'):
                        partner_id = int(part.split(':')[1])
                        partner = Partner.objects.get(id=partner_id)
                        return Response({
                            'is_impersonating': True,
                            'partner': PartnerSerializer(partner).data
                        })
    except (AccessToken.DoesNotExist, Partner.DoesNotExist, ValueError):
        pass
    
    return Response({
        'is_impersonating': False,
        'partner': None
    })
