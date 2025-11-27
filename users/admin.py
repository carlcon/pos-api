from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'role', 'employee_id', 'is_active_employee', 'is_staff']
    list_filter = ['role', 'is_active_employee', 'is_staff', 'is_superuser']
    search_fields = ['username', 'email', 'employee_id', 'first_name', 'last_name']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('role', 'phone', 'employee_id', 'is_active_employee')
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('role', 'phone', 'employee_id', 'is_active_employee')
        }),
    )
