from django.contrib import admin
from users.admin import PartnerScopedAdmin
from .models import Store


@admin.register(Store)
class StoreAdmin(PartnerScopedAdmin):
    list_display = ['name', 'code', 'partner', 'is_default', 'is_active', 'created_at']
    list_filter = ['is_active', 'is_default', 'created_at']
    search_fields = ['name', 'code', 'contact_email', 'contact_phone']
    readonly_fields = ['created_at', 'updated_at']
