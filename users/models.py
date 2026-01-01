from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError
import random
import string


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
    
    # Barcode configuration
    class BarcodeFormat(models.TextChoices):
        EAN13 = 'EAN13', 'EAN-13'
        CODE128 = 'CODE128', 'Code 128'
        CUSTOM = 'CUSTOM', 'Custom'
    
    barcode_format = models.CharField(
        max_length=20,
        choices=BarcodeFormat.choices,
        default=BarcodeFormat.EAN13,
        help_text='Barcode format for product barcodes'
    )
    barcode_prefix = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text='Optional prefix for custom barcode generation'
    )
    barcode_counter = models.PositiveIntegerField(
        default=1,
        help_text='Counter for sequential barcode generation'
    )
    
    class Meta:
        db_table = 'partners'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    def generate_barcode(self):
        """Generate a unique barcode based on partner's format settings."""
        from django.utils import timezone
        
        if self.barcode_format == self.BarcodeFormat.EAN13:
            # EAN-13 format: 12 digits + checksum
            prefix = self.barcode_prefix or str(self.id).zfill(3)[:3]
            counter = str(self.barcode_counter).zfill(9)[:9]
            barcode_base = prefix + counter
            # Calculate EAN-13 checksum
            total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(barcode_base[:12].zfill(12)))
            checksum = (10 - (total % 10)) % 10
            barcode = barcode_base[:12].zfill(12) + str(checksum)
        elif self.barcode_format == self.BarcodeFormat.CODE128:
            prefix = self.barcode_prefix or self.code[:5].upper()
            timestamp = timezone.now().strftime('%y%m%d%H%M')
            random_suffix = ''.join(random.choices(string.digits, k=4))
            barcode = f"{prefix}{timestamp}{random_suffix}"
        else:
            # Custom format
            prefix = self.barcode_prefix or self.code
            barcode = f"{prefix}{str(self.barcode_counter).zfill(8)}"
        
        # Increment counter
        self.barcode_counter += 1
        self.save(update_fields=['barcode_counter'])
        
        return barcode
    
    def generate_sku(self):
        """Generate a unique SKU for products."""
        sku = f"{self.code}-{str(self.barcode_counter).zfill(6)}"
        return sku


class User(AbstractUser):
    """
    Custom User model extending AbstractUser with role-based access control.
    
    Roles:
    - ADMIN: Partner-level admin (manages all stores under partner)
    - STORE_ADMIN: Store-level admin (manages single assigned store)
    - INVENTORY_STAFF: Can manage inventory
    - CASHIER: Can only access POS
    - VIEWER: Read-only access
    
    User Types:
    - Super Admin: is_super_admin=True, partner=None (can access all partners)
    - Partner User: is_super_admin=False, partner=Partner (scoped to one partner)
    - Store User: role=STORE_ADMIN/CASHIER, assigned_store=Store (scoped to one store)
    """
    
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        STORE_ADMIN = 'STORE_ADMIN', 'Store Admin'
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
    sms_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text='Phone number for SMS notifications'
    )
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
    
    # Store assignment (for STORE_ADMIN and CASHIER roles)
    assigned_store = models.ForeignKey(
        'stores.Store',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_users',
        help_text='Store assigned to this user (required for STORE_ADMIN and CASHIER roles)'
    )
    
    class Meta:
        db_table = 'users'
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['assigned_store']),
            models.Index(fields=['partner', 'role']),
        ]
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def clean(self):
        """Validate role-based constraints."""
        super().clean()
        
        # STORE_ADMIN and CASHIER must have assigned_store
        if self.role in [self.Role.STORE_ADMIN, self.Role.CASHIER]:
            if not self.assigned_store:
                raise ValidationError({
                    'assigned_store': f'{self.get_role_display()} must be assigned to a store.'
                })
        
        # Other roles should not have assigned_store
        if self.role not in [self.Role.STORE_ADMIN, self.Role.CASHIER]:
            if self.assigned_store:
                raise ValidationError({
                    'assigned_store': f'{self.get_role_display()} should not be assigned to a store.'
                })
        
        # If assigned_store is set, partner must match store's partner
        if self.assigned_store and self.partner:
            if self.assigned_store.partner_id != self.partner_id:
                raise ValidationError({
                    'assigned_store': 'Store must belong to the same partner as the user.'
                })
    
    def save(self, *args, **kwargs):
        # Auto-set partner from assigned_store if not set
        if self.assigned_store and not self.partner:
            self.partner = self.assigned_store.partner
        super().save(*args, **kwargs)
    
    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN
    
    @property
    def is_store_admin(self):
        return self.role == self.Role.STORE_ADMIN
    
    @property
    def is_inventory_staff(self):
        return self.role == self.Role.INVENTORY_STAFF
    
    @property
    def is_cashier(self):
        return self.role == self.Role.CASHIER
    
    @property
    def is_viewer(self):
        return self.role == self.Role.VIEWER
    
    @property
    def is_store_level_user(self):
        """Check if user is scoped to a specific store."""
        return self.role in [self.Role.STORE_ADMIN, self.Role.CASHIER]


class StoreAdminAuditLog(models.Model):
    """
    Audit log for Store Admin assignment changes.
    Tracks when store admins are assigned, moved, or removed from stores.
    """
    class Action(models.TextChoices):
        ASSIGNED = 'ASSIGNED', 'Assigned to Store'
        MOVED = 'MOVED', 'Moved to Different Store'
        REMOVED = 'REMOVED', 'Removed from Store'
        ROLE_CHANGED = 'ROLE_CHANGED', 'Role Changed'
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='store_audit_logs'
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    old_store = models.ForeignKey(
        'stores.Store',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs_old'
    )
    new_store = models.ForeignKey(
        'stores.Store',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs_new'
    )
    old_role = models.CharField(max_length=20, blank=True, null=True)
    new_role = models.CharField(max_length=20, blank=True, null=True)
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs_made'
    )
    reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'store_admin_audit_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.action} - {self.created_at}"
