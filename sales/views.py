from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from users.permissions import IsCashierOrAbove
from users.mixins import PartnerFilterMixin, require_partner_for_request
from .models import Sale, SaleItem
from .serializers import SaleSerializer, SaleCreateSerializer


class SaleListCreateView(PartnerFilterMixin, generics.ListCreateAPIView):
    """List all sales or create new sale"""
    queryset = Sale.objects.select_related('cashier').prefetch_related('items__product').all()
    permission_classes = [IsAuthenticated, IsCashierOrAbove]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return SaleCreateSerializer
        return SaleSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by store
        store_id = self.request.query_params.get('store_id')
        if store_id:
            queryset = queryset.filter(store_id=store_id)

        # Filter by date range
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        # Filter by cashier
        cashier = self.request.query_params.get('cashier', None)
        if cashier:
            queryset = queryset.filter(cashier_id=cashier)
        
        # Filter by payment method
        payment_method = self.request.query_params.get('payment_method', None)
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method.upper())
        
        return queryset


class SaleDetailView(PartnerFilterMixin, generics.RetrieveAPIView):
    """Retrieve a sale"""
    queryset = Sale.objects.select_related('cashier').prefetch_related('items__product').all()
    serializer_class = SaleSerializer
    permission_classes = [IsAuthenticated]


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sales_summary(request):
    """Get sales summary statistics"""
    partner = require_partner_for_request(request)
    store_id = request.query_params.get('store_id')
    
    # Get date filters
    period = request.query_params.get('period', 'today')  # today, week, month
    
    now = timezone.now()
    if period == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'week':
        start_date = now - timedelta(days=7)
    elif period == 'month':
        start_date = now - timedelta(days=30)
    else:
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    sales = Sale.objects.filter(created_at__gte=start_date)
    if partner:
        sales = sales.filter(partner=partner)
    if store_id:
        sales = sales.filter(store_id=store_id)
    
    total_sales = sales.aggregate(
        count=Count('id'),
        total_amount=Sum('total_amount')
    )
    
    return Response({
        'period': period,
        'total_sales_count': total_sales['count'] or 0,
        'total_revenue': float(total_sales['total_amount'] or 0),
        'start_date': start_date,
        'end_date': now
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def top_selling_products(request):
    """Get top-selling products"""
    partner = require_partner_for_request(request)
    store_id = request.query_params.get('store_id')
    
    limit = int(request.query_params.get('limit', 10))
    period = request.query_params.get('period', 'month')
    
    now = timezone.now()
    if period == 'week':
        start_date = now - timedelta(days=7)
    elif period == 'month':
        start_date = now - timedelta(days=30)
    else:
        start_date = now - timedelta(days=30)
    
    queryset = SaleItem.objects.filter(sale__created_at__gte=start_date)
    if partner:
        queryset = queryset.filter(sale__partner=partner)
    if store_id:
        queryset = queryset.filter(sale__store_id=store_id)
    
    top_products = (
        queryset
        .values('product__id', 'product__name', 'product__sku')
        .annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum('line_total')
        )
        .order_by('-total_quantity')[:limit]
    )
    
    return Response(list(top_products))
