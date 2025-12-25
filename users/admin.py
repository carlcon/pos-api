from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Partner, User


class PartnerScopedAdmin(admin.ModelAdmin):
    """Restrict queryset to request user's partner unless super admin."""

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if getattr(request.user, 'is_super_admin', False):
            return qs
        partner = getattr(request.user, 'partner', None)
        if partner:
            return qs.filter(partner=partner)
        return qs.none()

    def save_model(self, request, obj, form, change):
        if not getattr(request.user, 'is_super_admin', False):
            if hasattr(obj, 'partner') and not obj.partner:
                obj.partner = getattr(request.user, 'partner', None)
        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        readonly = tuple(super().get_readonly_fields(request, obj))
        if getattr(request.user, 'is_super_admin', False):
            return readonly
        return readonly + ("partner",) if hasattr(self.model, 'partner') else readonly


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active', 'created_at', 'updated_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'code', 'contact_email', 'contact_phone']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'role', 'employee_id', 'partner', 'is_super_admin', 'is_active_employee', 'is_staff']
    list_filter = ['role', 'partner', 'is_active_employee', 'is_staff', 'is_superuser', 'is_super_admin']
    search_fields = ['username', 'email', 'employee_id', 'first_name', 'last_name']

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('role', 'phone', 'employee_id', 'is_active_employee', 'partner', 'is_super_admin')
        }),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('role', 'phone', 'employee_id', 'is_active_employee', 'partner', 'is_super_admin')
        }),
    )
