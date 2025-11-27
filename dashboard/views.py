# Dashboard views for statistics and reports
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from inventory.models import Product
from sales.models import Sale
from stock.models import StockTransaction


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """
    Get comprehensive dashboard statistics
    """
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)
    
    # Today's sales
    today_sales = Sale.objects.filter(created_at__date=today).aggregate(
        total=Sum('total_amount'),
        count=Count('id')
    )
    
    yesterday_sales = Sale.objects.filter(created_at__date=yesterday).aggregate(
        total=Sum('total_amount')
    )
    
    today_total = float(today_sales['total'] or 0)
    yesterday_total = float(yesterday_sales['total'] or 0)
    sales_change = ((today_total - yesterday_total) / yesterday_total * 100) if yesterday_total > 0 else 0
    
    # Low stock items
    low_stock_products = Product.objects.filter(
        current_stock__lte=F('minimum_stock_level'),
        is_active=True
    ).order_by('current_stock')[:10]
    
    # Total inventory value
    total_inventory = Product.objects.filter(is_active=True).aggregate(
        total=Sum(F('current_stock') * F('cost_price'))
    )
    inventory_value = float(total_inventory['total'] or 0)
    
    # Top selling products (last 30 days)
    thirty_days_ago = today - timedelta(days=30)
    from sales.models import SaleItem
    top_products = SaleItem.objects.filter(
        sale__created_at__gte=thirty_days_ago
    ).values(
        'product__id',
        'product__name',
        'product__sku'
    ).annotate(
        total_sold=Sum('quantity'),
        revenue=Sum(F('quantity') * F('unit_price'))
    ).order_by('-revenue')[:5]
    
    # Sales by payment method (today)
    payment_methods = Sale.objects.filter(
        created_at__date=today
    ).values('payment_method').annotate(
        total=Sum('total_amount'),
        count=Count('id')
    )
    
    # Recent sales
    recent_sales = Sale.objects.select_related('cashier').order_by('-created_at')[:10]
    
    # Weekly sales trend
    weekly_sales = []
    for i in range(7):
        date = today - timedelta(days=6-i)
        daily_sales = Sale.objects.filter(created_at__date=date).aggregate(
            total=Sum('total_amount'),
            count=Count('id')
        )
        weekly_sales.append({
            'date': date.isoformat(),
            'total': float(daily_sales['total'] or 0),
            'count': daily_sales['count'] or 0
        })
    
    # Monthly revenue (last 6 months)
    monthly_revenue = []
    for i in range(6):
        month_start = today.replace(day=1) - timedelta(days=30*i)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        monthly_total = Sale.objects.filter(
            created_at__date__gte=month_start,
            created_at__date__lte=month_end
        ).aggregate(total=Sum('total_amount'))
        
        monthly_revenue.insert(0, {
            'month': month_start.strftime('%b'),
            'revenue': float(monthly_total['total'] or 0)
        })
    
    # Stock summary
    stock_summary = {
        'total_products': Product.objects.count(),
        'active_products': Product.objects.filter(is_active=True).count(),
        'low_stock_count': Product.objects.filter(
            current_stock__lte=F('minimum_stock_level'),
            is_active=True
        ).count(),
        'out_of_stock_count': Product.objects.filter(current_stock=0, is_active=True).count()
    }
    
    return Response({
        'today_sales': {
            'total': f'{today_total:.2f}',
            'count': today_sales['count'] or 0,
            'change_percentage': round(sales_change, 2)
        },
        'low_stock_items': {
            'count': low_stock_products.count(),
            'items': [{
                'id': p.id,
                'name': p.name,
                'sku': p.sku,
                'current_stock': p.current_stock,
                'minimum_stock_level': p.minimum_stock_level
            } for p in low_stock_products]
        },
        'total_inventory_value': {
            'value': f'{inventory_value:.2f}',
            'change_percentage': 0  # Calculate based on your needs
        },
        'top_selling_products': [{
            'id': p['product__id'],
            'name': p['product__name'],
            'sku': p['product__sku'],
            'total_sold': p['total_sold'],
            'revenue': f"{float(p['revenue']):.2f}"
        } for p in top_products],
        'sales_by_payment_method': [{
            'payment_method': pm['payment_method'],
            'total': f"{float(pm['total']):.2f}",
            'count': pm['count']
        } for pm in payment_methods],
        'recent_sales': [{
            'id': s.id,
            'sale_number': s.sale_number,
            'total_amount': str(s.total_amount),
            'customer_name': s.customer_name,
            'created_at': s.created_at.isoformat(),
            'cashier_username': s.cashier.username
        } for s in recent_sales],
        'weekly_sales': weekly_sales,
        'monthly_revenue': monthly_revenue,
        'stock_summary': stock_summary
    })
