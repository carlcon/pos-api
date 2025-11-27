from django.contrib import admin
from .models import Category, Product, Supplier, PurchaseOrder, POItem


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at']
    search_fields = ['name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['sku', 'name', 'category', 'current_stock', 'minimum_stock_level', 
                   'cost_price', 'selling_price', 'is_active']
    list_filter = ['category', 'is_active', 'unit_of_measure']
    search_fields = ['sku', 'name', 'barcode', 'brand']
    readonly_fields = ['current_stock', 'created_at', 'updated_at']


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_person', 'email', 'phone', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'email', 'phone']


class POItemInline(admin.TabularInline):
    model = POItem
    extra = 1


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['po_number', 'supplier', 'status', 'order_date', 'created_by', 'created_at']
    list_filter = ['status', 'order_date']
    search_fields = ['po_number', 'supplier__name']
    readonly_fields = ['created_by', 'created_at', 'updated_at']
    inlines = [POItemInline]
