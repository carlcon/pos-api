from rest_framework import serializers
from decimal import Decimal
from .models import StockTransaction, ProductCostHistory


class StockTransactionSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    performed_by_username = serializers.CharField(source='performed_by.username', read_only=True)
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    
    class Meta:
        model = StockTransaction
        fields = [
            'id', 'product', 'product_name', 'product_sku',
            'transaction_type', 'transaction_type_display',
            'reason', 'reason_display', 'quantity',
            'quantity_before', 'quantity_after',
            'unit_cost', 'total_cost',
            'reference_number', 'notes',
            'performed_by', 'performed_by_username', 'store', 'store_name', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class StockAdjustmentSerializer(serializers.Serializer):
    """Serializer for manual stock adjustments"""
    product_id = serializers.IntegerField()
    barcode = serializers.CharField(required=False, allow_blank=True)
    store_id = serializers.IntegerField(required=False, allow_null=True)
    adjustment_type = serializers.ChoiceField(choices=['IN', 'OUT', 'ADJUSTMENT'])
    quantity = serializers.IntegerField(min_value=1)
    reason = serializers.ChoiceField(
        choices=['PURCHASE', 'SALE', 'DAMAGED', 'LOST', 'RECONCILIATION', 'RETURN', 'MANUAL']
    )
    unit_cost = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
        min_value=Decimal('0.00'),
        help_text='Cost per unit (only for IN transactions). Defaults to product cost_price.'
    )
    reference_number = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class ProductCostHistorySerializer(serializers.ModelSerializer):
    """Serializer for product cost history"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    changed_by_username = serializers.CharField(source='changed_by.username', read_only=True)
    cost_difference = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    percentage_change = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    stock_transaction_id = serializers.IntegerField(source='stock_transaction.id', read_only=True, allow_null=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    
    class Meta:
        model = ProductCostHistory
        fields = [
            'id', 'product', 'product_name', 'product_sku',
            'old_cost', 'new_cost', 'cost_difference', 'percentage_change',
            'stock_transaction', 'stock_transaction_id',
            'reason', 'changed_by', 'changed_by_username', 'store', 'store_name', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
