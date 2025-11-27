from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model extending AbstractUser with role-based access control.
    Roles: ADMIN, INVENTORY_STAFF, CASHIER, VIEWER
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
