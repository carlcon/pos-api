from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from decimal import Decimal
from users.permissions import IsInventoryStaffOrAdmin
from users.mixins import PartnerFilterMixin, get_partner_from_request
from inventory.models import Product
from .models import StockTransaction, ProductCostHistory
from .serializers import (
    StockTransactionSerializer,
    StockAdjustmentSerializer,
    ProductCostHistorySerializer
)


class StockTransactionListView(PartnerFilterMixin, generics.ListAPIView):
    """List all stock transactions"""
    queryset = StockTransaction.objects.select_related('product', 'performed_by').all()
    serializer_class = StockTransactionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by product
        product_id = self.request.query_params.get('product', None)
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        
        # Filter by transaction type
        transaction_type = self.request.query_params.get('type', None)
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type.upper())
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        return queryset


class StockTransactionDetailView(PartnerFilterMixin, generics.RetrieveAPIView):
    """Retrieve a stock transaction"""
    queryset = StockTransaction.objects.select_related('product', 'performed_by').all()
    serializer_class = StockTransactionSerializer
    permission_classes = [IsAuthenticated]


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsInventoryStaffOrAdmin])
def stock_adjustment(request):
    """Manually adjust stock (IN/OUT/ADJUSTMENT for damaged, lost, reconciliation, etc.)"""
    partner = get_partner_from_request(request)
    serializer = StockAdjustmentSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    
    with transaction.atomic():
        # Get product (by ID or barcode)
        filter_kwargs = {}
        if partner:
            filter_kwargs['partner'] = partner
            
        if 'barcode' in data and data['barcode']:
            try:
                filter_kwargs['barcode'] = data['barcode']
                product = Product.objects.get(**filter_kwargs)
            except Product.DoesNotExist:
                return Response(
                    {'error': 'Product not found with this barcode'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            filter_kwargs['id'] = data['product_id']
            product = get_object_or_404(Product, **filter_kwargs)
        
        quantity = data['quantity']
        adjustment_type = data['adjustment_type']
        
        # Check if we have enough stock for OUT adjustments
        if adjustment_type == 'OUT' and product.current_stock < quantity:
            return Response(
                {'error': f'Insufficient stock. Available: {product.current_stock}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update product stock
        quantity_before = product.current_stock
        
        if adjustment_type == 'IN':
            product.current_stock += quantity
        elif adjustment_type == 'OUT':
            product.current_stock -= quantity
        else:  # ADJUSTMENT - set to exact quantity
            product.current_stock = quantity
        
        # Handle cost tracking for IN transactions
        unit_cost = None
        total_cost = None
        cost_changed = False
        old_cost = product.cost_price
        
        if adjustment_type == 'IN':
            # Get unit_cost from request or default to product's cost_price
            unit_cost = data.get('unit_cost')
            if unit_cost is None:
                unit_cost = product.cost_price
            else:
                unit_cost = Decimal(str(unit_cost))
            
            # Calculate total cost
            total_cost = unit_cost * quantity
            
            # Update product cost_price if different
            if unit_cost != old_cost:
                product.cost_price = unit_cost
                cost_changed = True
        
        product.save()
        
        # Create stock transaction
        stock_transaction = StockTransaction.objects.create(
            product=product,
            partner=partner,
            transaction_type=adjustment_type,
            reason=data['reason'],
            quantity=quantity,
            quantity_before=quantity_before,
            quantity_after=product.current_stock,
            unit_cost=unit_cost,
            total_cost=total_cost,
            reference_number=data.get('reference_number', ''),
            notes=data.get('notes', ''),
            performed_by=request.user
        )
        
        # Create cost history record if cost changed
        if cost_changed:
            ProductCostHistory.objects.create(
                product=product,
                old_cost=old_cost,
                new_cost=unit_cost,
                stock_transaction=stock_transaction,
                reason=f"Stock IN - {data['reason']}",
                changed_by=request.user
            )
    
    return Response({
        'message': 'Stock adjusted successfully',
        'transaction': StockTransactionSerializer(stock_transaction).data,
        'cost_updated': cost_changed
    })


class ProductCostHistoryListView(PartnerFilterMixin, generics.ListAPIView):
    """List product cost history (Admin and Inventory Staff only)"""
    serializer_class = ProductCostHistorySerializer
    permission_classes = [IsAuthenticated, IsInventoryStaffOrAdmin]
    partner_field = 'product__partner'  # Filter through product's partner
    
    def get_queryset(self):
        queryset = ProductCostHistory.objects.select_related(
            'product', 'changed_by', 'stock_transaction'
        ).all()
        
        # Apply partner filter
        partner = get_partner_from_request(self.request)
        if partner:
            queryset = queryset.filter(product__partner=partner)
        
        # Filter by product
        product_id = self.request.query_params.get('product', None)
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        return queryset


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def low_stock_products(request):
    """Get products with stock below minimum level"""
    from inventory.serializers import ProductSerializer
    
    partner = get_partner_from_request(request)
    products = Product.objects.select_related('category').all()
    if partner:
        products = products.filter(partner=partner)
    
    low_stock = [p for p in products if p.is_low_stock and p.is_active]
    
    serializer = ProductSerializer(low_stock, many=True)
    return Response({
        'count': len(low_stock),
        'products': serializer.data
    })
