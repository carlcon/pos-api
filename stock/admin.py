from django.contrib import admin
from .models import StockTransaction


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ['product', 'transaction_type', 'reason', 'quantity', 
                   'quantity_before', 'quantity_after', 'performed_by', 'created_at']
    list_filter = ['transaction_type', 'reason', 'created_at']
    search_fields = ['product__name', 'product__sku', 'reference_number']
    readonly_fields = ['created_at']
