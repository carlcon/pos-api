from django.contrib import admin
from .models import StockTransaction, ProductCostHistory


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ['product', 'transaction_type', 'reason', 'quantity', 
                   'quantity_before', 'quantity_after', 'unit_cost', 'total_cost',
                   'performed_by', 'created_at']
    list_filter = ['transaction_type', 'reason', 'created_at']
    search_fields = ['product__name', 'product__sku', 'reference_number']
    readonly_fields = ['created_at']


@admin.register(ProductCostHistory)
class ProductCostHistoryAdmin(admin.ModelAdmin):
    list_display = ['product', 'old_cost', 'new_cost', 'cost_difference', 
                   'percentage_change', 'reason', 'changed_by', 'created_at']
    list_filter = ['created_at', 'reason']
    search_fields = ['product__name', 'product__sku', 'reason']
    readonly_fields = ['created_at', 'cost_difference', 'percentage_change']
    raw_id_fields = ['product', 'stock_transaction', 'changed_by']
    
    def cost_difference(self, obj):
        return f"₱{obj.cost_difference:.2f}"
    cost_difference.short_description = 'Difference'
    
    def percentage_change(self, obj):
        return f"{obj.percentage_change:.1f}%"
    percentage_change.short_description = 'Change %'
