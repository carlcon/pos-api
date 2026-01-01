from django.contrib import admin
from users.admin import PartnerScopedAdmin
from .models import Category, Product, Supplier, PurchaseOrder, POItem, StoreInventory


@admin.register(Category)
class CategoryAdmin(PartnerScopedAdmin):
    list_display = ['name', 'partner', 'description', 'created_at']
    list_filter = ['partner']
    search_fields = ['name']


@admin.register(Product)
class ProductAdmin(PartnerScopedAdmin):
    list_display = ['sku', 'name', 'partner', 'category', 'cost_price', 'selling_price', 'is_active']
    list_filter = ['partner', 'category', 'is_active', 'unit_of_measure']
    search_fields = ['sku', 'name', 'barcode', 'brand']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Supplier)
class SupplierAdmin(PartnerScopedAdmin):
    list_display = ['name', 'partner', 'contact_person', 'email', 'phone', 'is_active']
    list_filter = ['partner', 'is_active']
    search_fields = ['name', 'email', 'phone']


class POItemInline(admin.TabularInline):
    model = POItem
    extra = 1


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(PartnerScopedAdmin):
    list_display = ['po_number', 'partner', 'supplier', 'status', 'order_date', 'created_by', 'created_at']
    list_filter = ['partner', 'status', 'order_date']
    search_fields = ['po_number', 'supplier__name']
    readonly_fields = ['created_by', 'created_at', 'updated_at']
    inlines = [POItemInline]


@admin.register(StoreInventory)
class StoreInventoryAdmin(admin.ModelAdmin):
    list_display = ['product', 'store', 'current_stock', 'minimum_stock_level', 'is_low_stock', 'updated_at']
    list_filter = ['store', 'product__category']
    search_fields = ['product__name', 'product__sku', 'store__name']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Only show inventory for products belonging to user's partner
        if hasattr(request.user, 'partner') and request.user.partner:
            qs = qs.filter(product__partner=request.user.partner)
        return qs
