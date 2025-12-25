from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q
from users.permissions import IsInventoryStaffOrAdmin, CanDeleteProducts
from users.mixins import PartnerFilterMixin, require_partner_for_request
from .models import Category, Product, Supplier, PurchaseOrder, POItem
from .serializers import (
    CategorySerializer, ProductSerializer, ProductCreateUpdateSerializer,
    SupplierSerializer, PurchaseOrderSerializer, PurchaseOrderCreateSerializer,
    ReceiveItemSerializer
)
from stock.models import StockTransaction
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
        
        # Filter by low stock
        low_stock = self.request.query_params.get('low_stock', None)
        if low_stock == 'true':
            queryset = [p for p in queryset if p.is_low_stock]
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset


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
            
            # Update product stock
            product = po_item.product
            quantity_before = product.current_stock
            product.current_stock += received_qty
            product.save()
            
            # Create stock transaction
            StockTransaction.objects.create(
                product=product,
                partner=partner,
                transaction_type='IN',
                reason='PURCHASE',
                quantity=received_qty,
                quantity_before=quantity_before,
                quantity_after=product.current_stock,
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
