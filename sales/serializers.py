from rest_framework import serializers
from .models import Sale, SaleItem
from inventory.serializers import ProductSerializer


class SaleItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    
    class Meta:
        model = SaleItem
        fields = [
            'id', 'product', 'product_name', 'product_sku',
            'quantity', 'unit_price', 'discount', 'line_total'
        ]
        read_only_fields = ['id', 'line_total']


class SaleItemCreateSerializer(serializers.ModelSerializer):
    barcode = serializers.CharField(required=False, write_only=True)
    
    class Meta:
        model = SaleItem
        fields = ['product', 'quantity', 'unit_price', 'discount', 'barcode']


class SaleSerializer(serializers.ModelSerializer):
    cashier_username = serializers.CharField(source='cashier.username', read_only=True)
    items = SaleItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Sale
        fields = [
            'id', 'sale_number', 'customer_name', 'payment_method', 'is_wholesale',
            'subtotal', 'discount', 'total_amount', 'notes',
            'cashier', 'cashier_username', 'items', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'total_amount']


class SaleCreateSerializer(serializers.ModelSerializer):
    items = SaleItemCreateSerializer(many=True)
    
    class Meta:
        model = Sale
        fields = [
            'sale_number', 'customer_name', 'payment_method', 'is_wholesale',
            'subtotal', 'discount', 'notes', 'items'
        ]
        extra_kwargs = {
            'sale_number': {'required': False},
            'subtotal': {'required': False},
            'is_wholesale': {'required': False},
        }
    
    def validate(self, data):
        """Validate that items list is not empty"""
        if not data.get('items'):
            raise serializers.ValidationError({'items': 'At least one item is required'})
        return data
    
    def create(self, validated_data):
        from inventory.models import Product
        from stock.models import StockTransaction
        from django.db import transaction
        from django.utils import timezone
        import uuid
        
        items_data = validated_data.pop('items')
        validated_data['cashier'] = self.context['request'].user
        
        # Auto-generate sale_number if not provided
        if not validated_data.get('sale_number'):
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            validated_data['sale_number'] = f"SALE-{timestamp}-{str(uuid.uuid4())[:4].upper()}"
        
        with transaction.atomic():
            # Calculate totals
            subtotal = sum(
                item['unit_price'] * item['quantity'] - item.get('discount', 0)
                for item in items_data
            )
            validated_data['subtotal'] = subtotal
            validated_data['total_amount'] = subtotal - validated_data.get('discount', 0)
            
            # Create sale
            sale = Sale.objects.create(**validated_data)
            
            # Create sale items and update stock
            for item_data in items_data:
                # Handle barcode lookup if provided
                if 'barcode' in item_data:
                    barcode = item_data.pop('barcode')
                    try:
                        product = Product.objects.get(barcode=barcode)
                        item_data['product'] = product
                    except Product.DoesNotExist:
                        raise serializers.ValidationError(
                            {'barcode': f'No product found with barcode {barcode}'}
                        )
                
                product = item_data['product']
                quantity = item_data['quantity']
                
                # Check stock availability
                if product.current_stock < quantity:
                    raise serializers.ValidationError(
                        {'stock': f'Insufficient stock for {product.name}. Available: {product.current_stock}'}
                    )
                
                # Create sale item
                line_total = (item_data['unit_price'] * quantity) - item_data.get('discount', 0)
                sale_item = SaleItem.objects.create(
                    sale=sale,
                    product=product,
                    quantity=quantity,
                    unit_price=item_data['unit_price'],
                    discount=item_data.get('discount', 0),
                    line_total=line_total
                )
                
                # Update product stock
                quantity_before = product.current_stock
                product.current_stock -= quantity
                product.save()
                
                # Create stock transaction
                StockTransaction.objects.create(
                    product=product,
                    transaction_type='OUT',
                    reason='SALE',
                    quantity=quantity,
                    quantity_before=quantity_before,
                    quantity_after=product.current_stock,
                    reference_number=sale.sale_number,
                    performed_by=self.context['request'].user
                )
        
        return sale
