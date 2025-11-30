from rest_framework import permissions
from users.models import User


class IsSuperAdmin(permissions.BasePermission):
    """Only Super Admin users have access"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_super_admin


class IsAdmin(permissions.BasePermission):
    """Only Admin users have access"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_admin


class IsAdminOrSuperAdmin(permissions.BasePermission):
    """Admin or Super Admin users have access"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            (request.user.is_admin or request.user.is_super_admin)
        )


class IsInventoryStaffOrAdmin(permissions.BasePermission):
    """Inventory Staff and Admin have access"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in [User.Role.ADMIN, User.Role.INVENTORY_STAFF]
        )


class IsCashierOrAbove(permissions.BasePermission):
    """Cashier, Inventory Staff, and Admin have access"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in [User.Role.ADMIN, User.Role.INVENTORY_STAFF, User.Role.CASHIER]
        )


class CanDeleteProducts(permissions.BasePermission):
    """Only Admin can delete products"""
    
    def has_permission(self, request, view):
        if request.method == 'DELETE':
            return request.user and request.user.is_authenticated and request.user.is_admin
        return True


class CanAdjustStock(permissions.BasePermission):
    """Only Inventory Staff and Admin can adjust stock"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in [User.Role.ADMIN, User.Role.INVENTORY_STAFF]
        )


class CanDeleteTransactions(permissions.BasePermission):
    """Only Admin can delete transactions"""
    
    def has_permission(self, request, view):
        if request.method == 'DELETE':
            return request.user and request.user.is_authenticated and request.user.is_admin
        return True
