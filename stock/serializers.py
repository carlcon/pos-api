from rest_framework import serializers
from .models import StockTransaction


class StockTransactionSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    performed_by_username = serializers.CharField(source='performed_by.username', read_only=True)
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    
    class Meta:
        model = StockTransaction
        fields = [
            'id', 'product', 'product_name', 'product_sku',
            'transaction_type', 'transaction_type_display',
            'reason', 'reason_display', 'quantity',
            'quantity_before', 'quantity_after', 'reference_number',
            'notes', 'performed_by', 'performed_by_username', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class StockAdjustmentSerializer(serializers.Serializer):
    """Serializer for manual stock adjustments"""
    product_id = serializers.IntegerField()
    barcode = serializers.CharField(required=False, allow_blank=True)
    adjustment_type = serializers.ChoiceField(choices=['IN', 'OUT'])
    quantity = serializers.IntegerField(min_value=1)
    reason = serializers.ChoiceField(
        choices=['DAMAGED', 'LOST', 'RECONCILIATION', 'RETURN', 'MANUAL']
    )
    notes = serializers.CharField(required=False, allow_blank=True)
