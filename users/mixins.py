"""
Partner filtering mixins for multi-tenant data isolation.
"""
from rest_framework.exceptions import PermissionDenied
from oauth2_provider.models import AccessToken
from users.models import Partner


IMPERSONATION_REQUIRED_MESSAGE = "Super admin must impersonate a partner to access tenant data."


def get_partner_from_request(request):
    """
    Get the effective partner for the current request.
    
    Logic:
    1. If user is impersonating (token scope contains impersonating:X), use that partner
    2. If user has a partner assigned, use that partner
    3. If user is super_admin without impersonation, return None (must select partner first)
    
    Returns:
        Partner instance or None
    """
    user = request.user
    
    if not user.is_authenticated:
        return None
    
    # Check for impersonation token
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if auth_header.startswith('Bearer '):
        token_string = auth_header.split(' ')[1]
        try:
            access_token = AccessToken.objects.get(token=token_string)
            if 'impersonating:' in access_token.scope:
                # Extract partner ID from scope
                scope_parts = access_token.scope.split()
                for part in scope_parts:
                    if part.startswith('impersonating:'):
                        partner_id = int(part.split(':')[1])
                        return Partner.objects.get(id=partner_id)
        except (AccessToken.DoesNotExist, Partner.DoesNotExist, ValueError):
            pass
    
    # Return user's assigned partner (may be None for super admins)
    return user.partner


def require_partner_for_request(request, *, required=True):
    """Return partner or raise a helpful 403 when partner is required and missing."""
    partner = get_partner_from_request(request)

    if partner is None and required:
        user = getattr(request, 'user', None)
        if getattr(user, 'is_super_admin', False):
            raise PermissionDenied(IMPERSONATION_REQUIRED_MESSAGE)
        raise PermissionDenied("User not associated with any partner.")

    return partner


class PartnerFilterMixin:
    """
    Mixin for filtering querysets by partner.
    
    Usage:
        class ProductListCreateView(PartnerFilterMixin, generics.ListCreateAPIView):
            queryset = Product.objects.all()
            ...
    
    The mixin will:
    1. Filter GET requests to only show data belonging to the effective partner
    2. Auto-assign the effective partner on POST/create operations
    3. Raise PermissionDenied if super admin hasn't selected a partner (via impersonation)
    """
    
    partner_field = 'partner'  # Override if the FK field has a different name
    require_partner = True  # Set to False to allow super admins to see all data
    
    def get_effective_partner(self):
        """Get the partner for filtering/assignment."""
        return require_partner_for_request(self.request, required=self.require_partner)
    
    def get_queryset(self):
        """Filter queryset by partner."""
        queryset = super().get_queryset()
        partner = self.get_effective_partner()
        
        if partner is not None:
            filter_kwargs = {self.partner_field: partner}
            queryset = queryset.filter(**filter_kwargs)
        
        return queryset
    
    def perform_create(self, serializer):
        """Auto-assign partner on create."""
        partner = self.get_effective_partner()
        if partner is not None:
            serializer.save(**{self.partner_field: partner})
        else:
            serializer.save()


class PartnerFilterViewSetMixin(PartnerFilterMixin):
    """
    Same as PartnerFilterMixin but for ViewSets.
    Handles both list and create operations.
    """
    pass


class OptionalPartnerFilterMixin(PartnerFilterMixin):
    """
    Like PartnerFilterMixin but doesn't require a partner.
    Super admins can see all data without impersonation.
    """
    require_partner = False
    
    def get_queryset(self):
        """Filter queryset by partner if one is set, otherwise return all."""
        queryset = super(PartnerFilterMixin, self).get_queryset()
        partner = get_partner_from_request(self.request)
        
        if partner is not None:
            filter_kwargs = {self.partner_field: partner}
            queryset = queryset.filter(**filter_kwargs)
        
        return queryset
