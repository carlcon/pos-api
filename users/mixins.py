"""
Partner and Store filtering mixins for multi-tenant data isolation.
"""
from rest_framework.exceptions import PermissionDenied
from oauth2_provider.models import AccessToken
from users.models import Partner


IMPERSONATION_REQUIRED_MESSAGE = "Super admin must impersonate a partner to access tenant data."
STORE_IMPERSONATION_REQUIRED_MESSAGE = "Partner admin must impersonate a store to access store-specific data."


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


def get_effective_store(request):
    """
    Get the effective store for the current request.
    
    Logic:
    1. If token scope contains impersonating_store:X, use that store
    2. If user has assigned_store (STORE_ADMIN/CASHIER), use that store
    3. Otherwise return None
    
    Returns:
        Store instance or None
    """
    from stores.models import Store
    
    user = request.user
    
    if not user.is_authenticated:
        return None
    
    # Check for store impersonation token
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if auth_header.startswith('Bearer '):
        token_string = auth_header.split(' ')[1]
        try:
            access_token = AccessToken.objects.get(token=token_string)
            # Check for store impersonation
            if 'impersonating_store:' in access_token.scope:
                scope_parts = access_token.scope.split()
                for part in scope_parts:
                    if part.startswith('impersonating_store:'):
                        store_id = int(part.split(':')[1])
                        return Store.objects.get(id=store_id)
        except (AccessToken.DoesNotExist, Store.DoesNotExist, ValueError):
            pass
    
    # Return user's assigned store (for STORE_ADMIN/CASHIER)
    return user.assigned_store


def get_store_id_from_request(request):
    """
    Get store_id from request query params, data, or effective store.
    Returns the store_id to filter by, or None for all stores.
    """
    # Check query params
    store_id = request.query_params.get('store_id') or request.query_params.get('store')
    if store_id:
        return int(store_id)
    
    # Check request data (for POST/PUT/PATCH)
    if hasattr(request, 'data'):
        store_id = request.data.get('store_id') or request.data.get('store')
        if store_id:
            return int(store_id)
    
    # Check effective store (from impersonation or assignment)
    effective_store = get_effective_store(request)
    if effective_store:
        return effective_store.id
    
    return None


def require_partner_for_request(request, *, required=True):
    """Return partner or raise a helpful 403 when partner is required and missing."""
    partner = get_partner_from_request(request)

    if partner is None and required:
        user = getattr(request, 'user', None)
        if getattr(user, 'is_super_admin', False):
            raise PermissionDenied(IMPERSONATION_REQUIRED_MESSAGE)
        raise PermissionDenied("User not associated with any partner.")

    return partner


def require_store_for_request(request, *, required=True):
    """Return store or raise a helpful 403 when store is required and missing."""
    store = get_effective_store(request)
    
    if store is None and required:
        user = getattr(request, 'user', None)
        if getattr(user, 'is_admin', False) or getattr(user, 'is_super_admin', False):
            raise PermissionDenied(STORE_IMPERSONATION_REQUIRED_MESSAGE)
        raise PermissionDenied("User not assigned to any store.")
    
    return store


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
    store_field = 'store'  # Override if the FK field has a different name
    require_partner = True  # Set to False to allow super admins to see all data
    filter_by_store = False  # Set to True to also filter by store
    
    def get_effective_partner(self):
        """Get the partner for filtering/assignment."""
        return require_partner_for_request(self.request, required=self.require_partner)
    
    def get_effective_store(self):
        """Get the store for filtering/assignment."""
        return get_effective_store(self.request)
    
    def get_queryset(self):
        """Filter queryset by partner and optionally by store."""
        queryset = super().get_queryset()
        partner = self.get_effective_partner()
        
        if partner is not None:
            filter_kwargs = {self.partner_field: partner}
            queryset = queryset.filter(**filter_kwargs)
        
        # Filter by store if enabled and store is available
        if self.filter_by_store:
            store = self.get_effective_store()
            if store is not None:
                filter_kwargs = {self.store_field: store}
                queryset = queryset.filter(**filter_kwargs)
            else:
                # Check if user is STORE_ADMIN/CASHIER - they must have a store
                user = self.request.user
                if user.is_store_level_user:
                    # This shouldn't happen as store-level users should always have assigned_store
                    queryset = queryset.none()
                else:
                    # Partner admin or above - check for store_id in query params
                    store_id = get_store_id_from_request(self.request)
                    if store_id:
                        queryset = queryset.filter(**{self.store_field + '_id': store_id})
        
        return queryset
    
    def perform_create(self, serializer):
        """Auto-assign partner and store on create."""
        partner = self.get_effective_partner()
        save_kwargs = {}
        
        if partner is not None:
            save_kwargs[self.partner_field] = partner
        
        if self.filter_by_store:
            store = self.get_effective_store()
            if store is not None:
                save_kwargs[self.store_field] = store
        
        if save_kwargs:
            serializer.save(**save_kwargs)
        else:
            serializer.save()


class PartnerFilterViewSetMixin(PartnerFilterMixin):
    """
    Same as PartnerFilterMixin but for ViewSets.
    Handles both list and create operations.
    """
    pass


class StoreFilterMixin(PartnerFilterMixin):
    """
    Mixin for filtering querysets by both partner and store.
    Use this for store-level data like stock transactions.
    """
    filter_by_store = True
    require_store = False  # Set to True to require store impersonation
    
    def get_queryset(self):
        """Filter queryset by partner and store."""
        queryset = super().get_queryset()
        
        if self.require_store:
            store = require_store_for_request(self.request, required=True)
            if store:
                queryset = queryset.filter(**{self.store_field: store})
        
        return queryset


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
