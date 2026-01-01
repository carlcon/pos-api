from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction, models
from django.db.models import Q
from users.permissions import IsInventoryStaffOrAdmin, CanDeleteProducts
from users.mixins import PartnerFilterMixin, require_partner_for_request, get_store_id_from_request
from .models import Category, Product, Supplier, PurchaseOrder, POItem, StoreInventory
from .serializers import (
    CategorySerializer, ProductSerializer, ProductCreateUpdateSerializer,
    SupplierSerializer, PurchaseOrderSerializer, PurchaseOrderCreateSerializer,
    ReceiveItemSerializer, StoreInventorySerializer
)
from stock.models import StockTransaction
from stores.utils import get_default_store
from stores.models import Store
from .barcode_utils import generate_product_label_pdf, generate_multiple_labels_pdf


# Category Views
class CategoryListCreateView(PartnerFilterMixin, generics.ListCreateAPIView):
    """List all categories or create new category"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsInventoryStaffOrAdmin()]
        return [IsAuthenticated()]


class CategoryDetailView(PartnerFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a category"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, IsInventoryStaffOrAdmin]


# Product Views
class ProductListCreateView(PartnerFilterMixin, generics.ListCreateAPIView):
    """List all products or create new product"""
    queryset = Product.objects.select_related('category').all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProductCreateUpdateSerializer
        return ProductSerializer
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsInventoryStaffOrAdmin()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by store for store-level users
        store_id = get_store_id_from_request(self.request)
        if store_id:
            # Store-level users: show only products available at their store
            # Products with no stores assigned are available to all stores
            queryset = queryset.filter(
                models.Q(available_stores__id=store_id) | 
                models.Q(available_stores__isnull=True)
            ).distinct()
        
        # Filter by search query
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(sku__icontains=search) |
                Q(name__icontains=search) |
                Q(barcode__icontains=search)
            )
        
        # Filter by category
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category_id=category)
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset
    
    def get_serializer_context(self):
        """Add store_id to serializer context for stock filtering"""
        context = super().get_serializer_context()
        store_id = get_store_id_from_request(self.request)
        if store_id:
            context['request'].store_id = store_id
        return context


class ProductDetailView(PartnerFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a product"""
    queryset = Product.objects.select_related('category').all()
    permission_classes = [IsAuthenticated, IsInventoryStaffOrAdmin, CanDeleteProducts]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ProductCreateUpdateSerializer
        return ProductSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def product_barcode_lookup(request, barcode):
    """Look up product by barcode"""
    partner = require_partner_for_request(request)
    try:
        product = Product.objects.select_related('category').get(barcode=barcode, partner=partner)
        serializer = ProductSerializer(product)
        return Response(serializer.data)
    except Product.DoesNotExist:
        return Response(
            {'error': 'Product not found with this barcode'},
            status=status.HTTP_404_NOT_FOUND
        )


# Store Inventory Views
class StoreInventoryListView(PartnerFilterMixin, generics.ListCreateAPIView):
    """List or create store inventory records"""
    queryset = StoreInventory.objects.select_related('product', 'store').all()
    serializer_class = StoreInventorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by store
        store_id = self.request.query_params.get('store_id')
        if store_id:
            queryset = queryset.filter(store_id=store_id)
        elif hasattr(self.request.user, 'assigned_store') and self.request.user.assigned_store:
            # Auto-filter for store-level users
            queryset = queryset.filter(store=self.request.user.assigned_store)
        
        # Filter by product
        product_id = self.request.query_params.get('product_id')
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        
        # Filter by low stock
        low_stock = self.request.query_params.get('low_stock')
        if low_stock == 'true':
            queryset = queryset.filter(current_stock__lte=models.F('minimum_stock_level'))
        
        return queryset


class StoreInventoryDetailView(PartnerFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete store inventory"""
    queryset = StoreInventory.objects.select_related('product', 'store').all()
    serializer_class = StoreInventorySerializer
    permission_classes = [IsAuthenticated, IsInventoryStaffOrAdmin]


# Supplier Views
class SupplierListCreateView(PartnerFilterMixin, generics.ListCreateAPIView):
    """List all suppliers or create new supplier"""
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsInventoryStaffOrAdmin()]
        return [IsAuthenticated()]


class SupplierDetailView(PartnerFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a supplier"""
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated, IsInventoryStaffOrAdmin]


# Purchase Order Views
class PurchaseOrderListCreateView(PartnerFilterMixin, generics.ListCreateAPIView):
    """List all purchase orders or create new PO"""
    queryset = PurchaseOrder.objects.select_related('supplier', 'created_by').prefetch_related('items__product').all()
    permission_classes = [IsAuthenticated, IsInventoryStaffOrAdmin]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PurchaseOrderCreateSerializer
        return PurchaseOrderSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by status
        po_status = self.request.query_params.get('status', None)
        if po_status:
            queryset = queryset.filter(status=po_status.upper())
        
        # Filter by supplier
        supplier = self.request.query_params.get('supplier', None)
        if supplier:
            queryset = queryset.filter(supplier_id=supplier)
        
        return queryset


class PurchaseOrderDetailView(PartnerFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a purchase order"""
    queryset = PurchaseOrder.objects.select_related('supplier', 'created_by').prefetch_related('items__product').all()
    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsAuthenticated, IsInventoryStaffOrAdmin]


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsInventoryStaffOrAdmin])
def receive_po_items(request, po_id):
    """Receive items from a purchase order and update stock"""
    partner = require_partner_for_request(request)
    purchase_order = get_object_or_404(PurchaseOrder, id=po_id, partner=partner)
    store = None
    # Get store_id from query params since request.data is the items array
    store_id = request.query_params.get('store_id') or request.GET.get('store_id')
    if store_id:
        store = get_object_or_404(Store, id=store_id, partner=partner) if partner else get_object_or_404(Store, id=store_id)
    elif partner:
        store = get_default_store(partner)
    
    if purchase_order.status == 'RECEIVED':
        return Response(
            {'error': 'This purchase order is already fully received'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    serializer = ReceiveItemSerializer(data=request.data, many=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    with transaction.atomic():
        for item_data in serializer.validated_data:
            po_item = get_object_or_404(POItem, id=item_data['item_id'], purchase_order=purchase_order)
            received_qty = item_data['received_quantity']
            
            # Verify barcode if provided
            if 'barcode' in item_data and item_data['barcode']:
                if po_item.product.barcode != item_data['barcode']:
                    return Response(
                        {'error': f'Barcode mismatch for product {po_item.product.name}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Check if we're not exceeding ordered quantity
            if po_item.received_quantity + received_qty > po_item.ordered_quantity:
                return Response(
                    {'error': f'Cannot receive more than ordered for {po_item.product.name}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update PO item
            po_item.received_quantity += received_qty
            po_item.save()
            
            # Ensure store is set
            if not store:
                return Response(
                    {'error': 'Store is required for receiving items'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get or create store inventory record
            product = po_item.product
            store_inventory, created = StoreInventory.objects.get_or_create(
                product=product,
                store=store,
                defaults={'current_stock': 0, 'minimum_stock_level': 10}
            )
            
            # Update store inventory stock
            quantity_before = store_inventory.current_stock
            store_inventory.current_stock += received_qty
            store_inventory.save()
            
            # Create stock transaction
            StockTransaction.objects.create(
                product=product,
                partner=partner,
                store=store,
                transaction_type='IN',
                reason='PURCHASE',
                quantity=received_qty,
                quantity_before=quantity_before,
                quantity_after=store_inventory.current_stock,
                reference_number=purchase_order.po_number,
                performed_by=request.user
            )
        
        # Update PO status
        if purchase_order.is_fully_received:
            purchase_order.status = 'RECEIVED'
        elif any(item.received_quantity > 0 for item in purchase_order.items.all()):
            purchase_order.status = 'PARTIAL'
        
        purchase_order.save()
    
    return Response({
        'message': 'Items received successfully',
        'po': PurchaseOrderSerializer(purchase_order).data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def print_product_label(request, product_id):
    """Generate and return barcode label PDF for a single product"""
    partner = require_partner_for_request(request)
    product = get_object_or_404(Product, id=product_id, partner=partner)
    label_size = request.query_params.get('size', '2x1')  # 2x1 or 3x2
    
    return generate_product_label_pdf(product, label_size)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def print_multiple_labels(request):
    """Generate and return barcode labels PDF for multiple products"""
    product_ids = request.data.get('product_ids', [])
    label_size = request.data.get('label_size', '2x1')
    
    if not product_ids:
        return Response(
            {'error': 'product_ids list is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    partner = require_partner_for_request(request)
    products = Product.objects.filter(id__in=product_ids, partner=partner)
    
    if not products.exists():
        return Response(
            {'error': 'No products found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    return generate_multiple_labels_pdf(products, label_size)
