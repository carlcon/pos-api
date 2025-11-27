from django.contrib import admin
from .models import Sale, SaleItem


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ['line_total']


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ['sale_number', 'customer_name', 'total_amount', 'payment_method', 
                   'cashier', 'created_at']
    list_filter = ['payment_method', 'created_at', 'cashier']
    search_fields = ['sale_number', 'customer_name']
    readonly_fields = ['cashier', 'subtotal', 'total_amount', 'created_at']
    inlines = [SaleItemInline]
