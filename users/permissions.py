from rest_framework import permissions
from users.models import User


class IsSuperAdmin(permissions.BasePermission):
    """Only Super Admin users have access"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_super_admin


class IsAdmin(permissions.BasePermission):
    """Only Partner Admin users have access"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_admin


class IsStoreAdmin(permissions.BasePermission):
    """Only Store Admin users have access"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_store_admin


class IsStoreAdminOrAbove(permissions.BasePermission):
    """Store Admin, Partner Admin, or Super Admin have access"""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return (
            request.user.is_super_admin or
            request.user.role in [User.Role.ADMIN, User.Role.STORE_ADMIN]
        )


class IsAdminOrSuperAdmin(permissions.BasePermission):
    """Admin or Super Admin users have access"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            (request.user.is_admin or request.user.is_super_admin)
        )


class IsInventoryStaffOrAdmin(permissions.BasePermission):
    """Inventory Staff, Store Admin, and Admin have access"""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Super admin always has access
        if request.user.is_super_admin:
            return True
        
        return request.user.role in [
            User.Role.ADMIN, User.Role.STORE_ADMIN, User.Role.INVENTORY_STAFF
        ]


class IsCashierOrAbove(permissions.BasePermission):
    """Cashier, Store Admin, Inventory Staff, and Admin have access"""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Super admin always has access
        if request.user.is_super_admin:
            return True
        
        return request.user.role in [
            User.Role.ADMIN, User.Role.STORE_ADMIN,
            User.Role.INVENTORY_STAFF, User.Role.CASHIER
        ]


class CanAccessPOS(permissions.BasePermission):
    """
    Store Admin, Cashier, or higher can access POS.
    Used for point-of-sale operations.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Super admin must impersonate to access POS
        if request.user.is_super_admin:
            # Check if impersonating a store
            from users.mixins import get_effective_store
            return get_effective_store(request) is not None
        
        # Partner admin must impersonate store to access POS
        if request.user.is_admin:
            from users.mixins import get_effective_store
            return get_effective_store(request) is not None
        
        # Store Admin and Cashier can access POS
        return request.user.role in [User.Role.STORE_ADMIN, User.Role.CASHIER]


class IsAssignedToStore(permissions.BasePermission):
    """
    Check if user is assigned to a specific store.
    Requires store_id in URL kwargs or request data.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Super admin and partner admin have access
        if request.user.is_super_admin or request.user.is_admin:
            return True
        
        # Store admin/cashier must be assigned to the store
        store_id = view.kwargs.get('store_id') or request.data.get('store_id')
        if store_id and request.user.assigned_store_id:
            return request.user.assigned_store_id == int(store_id)
        
        return False


class CanManageStores(permissions.BasePermission):
    """Only Partner Admin can manage stores"""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_super_admin or request.user.is_admin


class CanManagePartnerUsers(permissions.BasePermission):
    """Partner Admin and Super Admin can manage partner users"""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_super_admin or request.user.is_admin


class CanViewNotifications(permissions.BasePermission):
    """All authenticated users can view notifications"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class CanDeleteProducts(permissions.BasePermission):
    """Only Admin can delete products"""
    
    def has_permission(self, request, view):
        if request.method == 'DELETE':
            return request.user and request.user.is_authenticated and request.user.is_admin
        return True


class CanAdjustStock(permissions.BasePermission):
    """Only Inventory Staff, Admin, and Store Admin can adjust stock"""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user is impersonating a store
        from users.mixins import get_effective_store
        effective_store = get_effective_store(request)
        
        # Super admin or partner admin must impersonate store
        if request.user.is_super_admin or request.user.is_admin:
            return effective_store is not None
        
        return request.user.role in [User.Role.STORE_ADMIN, User.Role.INVENTORY_STAFF]


class CanDeleteTransactions(permissions.BasePermission):
    """Only Admin can delete transactions"""
    
    def has_permission(self, request, view):
        if request.method == 'DELETE':
            return request.user and request.user.is_authenticated and request.user.is_admin
        return True


class CanViewStock(permissions.BasePermission):
    """
    Store Admin, Cashier, or users impersonating a store can view stock.
    Partner Admin cannot view stock unless impersonating.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user is impersonating a store
        from users.mixins import get_effective_store
        effective_store = get_effective_store(request)
        
        # Super admin or partner admin must impersonate store to view stock
        if request.user.is_super_admin or request.user.is_admin:
            return effective_store is not None
        
        # Store Admin and Cashier can view stock
        return request.user.role in [User.Role.STORE_ADMIN, User.Role.CASHIER]
