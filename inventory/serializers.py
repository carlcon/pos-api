from rest_framework import serializers
from .models import Category, Product, Supplier, PurchaseOrder, POItem


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(source='products.count', read_only=True)
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'product_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    stock_value = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'sku', 'name', 'description', 'category', 'category_name',
            'brand', 'model_compatibility', 'unit_of_measure', 'cost_price',
            'selling_price', 'wholesale_price', 'minimum_stock_level', 'current_stock',
            'barcode', 'image', 'is_active', 'is_low_stock', 'stock_value',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'current_stock']


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'sku', 'name', 'description', 'category', 'brand',
            'model_compatibility', 'unit_of_measure', 'cost_price',
            'selling_price', 'wholesale_price', 'minimum_stock_level', 'barcode', 'image', 'is_active'
        ]


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = [
            'id', 'name', 'contact_person', 'email', 'phone',
            'address', 'notes', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class POItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    total_cost = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    remaining_quantity = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = POItem
        fields = [
            'id', 'product', 'product_name', 'product_sku',
            'ordered_quantity', 'received_quantity', 'unit_cost',
            'total_cost', 'remaining_quantity'
        ]
        read_only_fields = ['id']


class POItemCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = POItem
        fields = ['product', 'ordered_quantity', 'unit_cost']


class PurchaseOrderSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    items = POItemSerializer(many=True, read_only=True)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    is_fully_received = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'po_number', 'supplier', 'supplier_name', 'status',
            'order_date', 'expected_delivery_date', 'notes', 'created_by',
            'created_by_username', 'items', 'total_amount', 'is_fully_received',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PurchaseOrderCreateSerializer(serializers.ModelSerializer):
    items = POItemCreateSerializer(many=True)
    
    class Meta:
        model = PurchaseOrder
        fields = [
            'po_number', 'supplier', 'status', 'order_date',
            'expected_delivery_date', 'notes', 'items'
        ]
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        validated_data['created_by'] = self.context['request'].user
        purchase_order = PurchaseOrder.objects.create(**validated_data)
        
        for item_data in items_data:
            POItem.objects.create(purchase_order=purchase_order, **item_data)
        
        return purchase_order


class ReceiveItemSerializer(serializers.Serializer):
    """Serializer for receiving PO items"""
    item_id = serializers.IntegerField()
    received_quantity = serializers.IntegerField(min_value=1)
    barcode = serializers.CharField(required=False, allow_blank=True)
