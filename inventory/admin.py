from django.contrib import admin
from users.admin import PartnerScopedAdmin
from .models import Category, Product, Supplier, PurchaseOrder, POItem


@admin.register(Category)
class CategoryAdmin(PartnerScopedAdmin):
    list_display = ['name', 'partner', 'description', 'created_at']
    list_filter = ['partner']
    search_fields = ['name']


@admin.register(Product)
class ProductAdmin(PartnerScopedAdmin):
    list_display = ['sku', 'name', 'partner', 'category', 'current_stock', 'minimum_stock_level',
                   'cost_price', 'selling_price', 'is_active']
    list_filter = ['partner', 'category', 'is_active', 'unit_of_measure']
    search_fields = ['sku', 'name', 'barcode', 'brand']
    readonly_fields = ['current_stock', 'created_at', 'updated_at']


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
