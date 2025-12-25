from rest_framework import viewsets, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta

from users.mixins import PartnerFilterViewSetMixin, require_partner_for_request
from .models import Expense, ExpenseCategory
from .serializers import (
    ExpenseSerializer, 
    ExpenseCreateUpdateSerializer,
    ExpenseCategorySerializer
)


class ExpenseCategoryViewSet(PartnerFilterViewSetMixin, viewsets.ModelViewSet):
    """ViewSet for expense categories"""
    queryset = ExpenseCategory.objects.all()
    serializer_class = ExpenseCategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        return queryset


class ExpenseViewSet(PartnerFilterViewSetMixin, viewsets.ModelViewSet):
    """ViewSet for expenses CRUD"""
    queryset = Expense.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'payment_method']
    search_fields = ['title', 'description', 'vendor', 'receipt_number']
    ordering_fields = ['expense_date', 'amount', 'created_at']
    ordering = ['-expense_date']
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ExpenseCreateUpdateSerializer
        return ExpenseSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Date range filters
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(expense_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(expense_date__lte=end_date)
        
        # Amount range filters
        min_amount = self.request.query_params.get('min_amount')
        max_amount = self.request.query_params.get('max_amount')
        
        if min_amount:
            queryset = queryset.filter(amount__gte=min_amount)
        if max_amount:
            queryset = queryset.filter(amount__lte=max_amount)
        
        return queryset
    
    def perform_create(self, serializer):
        partner = require_partner_for_request(self.request)
        serializer.save(created_by=self.request.user, partner=partner)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def expense_stats(request):
    """Get expense statistics for dashboard"""
    partner = require_partner_for_request(request)
    today = timezone.now().date()
    
    # Base queryset filtered by partner
    base_queryset = Expense.objects.all()
    if partner:
        base_queryset = base_queryset.filter(partner=partner)
    
    # Current month
    month_start = today.replace(day=1)
    if today.month == 12:
        month_end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        month_end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    
    # Last month
    if today.month == 1:
        last_month_start = today.replace(year=today.year - 1, month=12, day=1)
        last_month_end = month_start - timedelta(days=1)
    else:
        last_month_start = today.replace(month=today.month - 1, day=1)
        last_month_end = month_start - timedelta(days=1)
    
    # Aggregate stats
    total_stats = base_queryset.aggregate(
        total_expenses=Sum('amount'),
        total_count=Count('id')
    )
    
    this_month = base_queryset.filter(
        expense_date__gte=month_start,
        expense_date__lte=month_end
    ).aggregate(total=Sum('amount'))
    
    last_month = base_queryset.filter(
        expense_date__gte=last_month_start,
        expense_date__lte=last_month_end
    ).aggregate(total=Sum('amount'))
    
    # By category
    by_category = list(
        base_queryset.values('category__name', 'category__color')
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('-total')[:10]
    )
    
    # By payment method
    by_payment_method = list(
        base_queryset.values('payment_method')
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('-total')
    )
    
    # Monthly trend (last 6 months)
    monthly_trend = []
    for i in range(6):
        if today.month - i <= 0:
            m_month = 12 + (today.month - i)
            m_year = today.year - 1
        else:
            m_month = today.month - i
            m_year = today.year
        
        m_start = today.replace(year=m_year, month=m_month, day=1)
        if m_month == 12:
            m_end = m_start.replace(year=m_year + 1, month=1, day=1) - timedelta(days=1)
        else:
            m_end = m_start.replace(month=m_month + 1, day=1) - timedelta(days=1)
        
        m_total = base_queryset.filter(
            expense_date__gte=m_start,
            expense_date__lte=m_end
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        monthly_trend.insert(0, {
            'month': m_start.strftime('%b %Y'),
            'total': float(m_total)
        })
    
    # Today's expenses
    today_expenses = base_queryset.filter(expense_date=today).aggregate(
        total=Sum('amount'),
        count=Count('id')
    )
    
    return Response({
        'total_expenses': float(total_stats['total_expenses'] or 0),
        'total_count': total_stats['total_count'] or 0,
        'this_month_total': float(this_month['total'] or 0),
        'last_month_total': float(last_month['total'] or 0),
        'today_total': float(today_expenses['total'] or 0),
        'today_count': today_expenses['count'] or 0,
        'by_category': by_category,
        'by_payment_method': by_payment_method,
        'monthly_trend': monthly_trend
    })

