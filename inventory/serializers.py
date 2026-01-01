from rest_framework import serializers
from django.db.models import Sum, Min, F
from django.db import models
from .models import Category, Product, Supplier, PurchaseOrder, POItem, StoreInventory
from stores.models import Store


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(source='products.count', read_only=True)
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'product_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class StoreInventorySerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    stock_value = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = StoreInventory
        fields = [
            'id', 'product', 'product_name', 'product_sku', 
            'store', 'store_name', 'current_stock', 'minimum_stock_level',
            'is_low_stock', 'stock_value', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    available_stores = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    available_store_names = serializers.SerializerMethodField()
    
    # Stock fields - aggregated from StoreInventory
    current_stock = serializers.SerializerMethodField()
    minimum_stock_level = serializers.SerializerMethodField()
    is_low_stock = serializers.SerializerMethodField()
    stock_value = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'sku', 'name', 'description', 'category', 'category_name',
            'brand', 'model_compatibility', 'unit_of_measure', 'cost_price',
            'selling_price', 'wholesale_price', 'current_stock', 'minimum_stock_level',
            'barcode', 'image', 'is_active', 'is_low_stock', 'stock_value',
            'available_stores', 'available_store_names',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_available_store_names(self, obj):
        return [store.name for store in obj.available_stores.all()]
    
    def get_current_stock(self, obj):
        """Aggregate stock from all store inventories"""
        request = self.context.get('request')
        if request and hasattr(request, 'store_id'):
            # If filtering by store, return stock for that specific store
            try:
                inv = StoreInventory.objects.get(product=obj, store_id=request.store_id)
                return inv.current_stock
            except StoreInventory.DoesNotExist:
                return 0
        # Return total stock across all stores
        total = StoreInventory.objects.filter(product=obj).aggregate(Sum('current_stock'))['current_stock__sum']
        return total or 0
    
    def get_minimum_stock_level(self, obj):
        """Get minimum stock level from store inventories"""
        request = self.context.get('request')
        if request and hasattr(request, 'store_id'):
            # If filtering by store, return minimum for that specific store
            try:
                inv = StoreInventory.objects.get(product=obj, store_id=request.store_id)
                return inv.minimum_stock_level
            except StoreInventory.DoesNotExist:
                return 10  # Default
        # Return minimum across all stores
        min_level = StoreInventory.objects.filter(product=obj).aggregate(Min('minimum_stock_level'))['minimum_stock_level__min']
        return min_level or 10
    
    def get_is_low_stock(self, obj):
        """Check if any store has low stock"""
        request = self.context.get('request')
        if request and hasattr(request, 'store_id'):
            try:
                inv = StoreInventory.objects.get(product=obj, store_id=request.store_id)
                return inv.is_low_stock
            except StoreInventory.DoesNotExist:
                return False
        # Check if any store has low stock
        return StoreInventory.objects.filter(product=obj).filter(
            current_stock__lte=F('minimum_stock_level')
        ).exists()
    
    def get_stock_value(self, obj):
        """Calculate stock value"""
        stock = self.get_current_stock(obj)
        return stock * obj.cost_price


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    available_stores = serializers.PrimaryKeyRelatedField(
        many=True, 
        queryset=Store.objects.all(),
        required=False,
        allow_empty=True
    )
    
    class Meta:
        model = Product
        fields = [
            'sku', 'name', 'description', 'category', 'brand',
            'model_compatibility', 'unit_of_measure', 'cost_price',
            'selling_price', 'wholesale_price', 
            'barcode', 'image', 'is_active', 'available_stores'
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
