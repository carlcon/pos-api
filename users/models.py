from django.contrib.auth.models import AbstractUser
from django.db import models


class Partner(models.Model):
    """
    Partner/Tenant model for multi-tenancy.
    Each partner represents a separate business/client.
    """
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(
        max_length=50, 
        unique=True,
        help_text='Unique identifier code for the partner (e.g., PARTNER001)'
    )
    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'partners'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class User(AbstractUser):
    """
    Custom User model extending AbstractUser with role-based access control.
    Roles: ADMIN, INVENTORY_STAFF, CASHIER, VIEWER
    
    User Types:
    - Super Admin: is_super_admin=True, partner=None (can access all partners)
    - Partner User: is_super_admin=False, partner=Partner (scoped to one partner)
    """
    
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        INVENTORY_STAFF = 'INVENTORY_STAFF', 'Inventory Staff'
        CASHIER = 'CASHIER', 'Cashier'
        VIEWER = 'VIEWER', 'Viewer'
    
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.VIEWER,
        help_text='User role for permission management'
    )
    phone = models.CharField(max_length=20, blank=True, null=True)
    employee_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    is_active_employee = models.BooleanField(default=True)
    
    # Multi-tenancy fields
    partner = models.ForeignKey(
        Partner,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='users',
        help_text='Partner/tenant this user belongs to. Null for super admins.'
    )
    is_super_admin = models.BooleanField(
        default=False,
        help_text='Super admins can manage all partners and impersonate partner users.'
    )
    
    class Meta:
        db_table = 'users'
        ordering = ['-date_joined']
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN
    
    @property
    def is_inventory_staff(self):
        return self.role == self.Role.INVENTORY_STAFF
    
    @property
    def is_cashier(self):
        return self.role == self.Role.CASHIER
    
    @property
    def is_viewer(self):
        return self.role == self.Role.VIEWER
