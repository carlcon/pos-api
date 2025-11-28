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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def daily_sales_report(request):
    """Get daily sales report for a specific date or date range"""
    from sales.models import SaleItem
    
    date_str = request.query_params.get('date', timezone.now().date().isoformat())
    try:
        report_date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        report_date = timezone.now().date()
    
    sales = Sale.objects.filter(created_at__date=report_date).select_related('cashier')
    
    # Summary
    summary = sales.aggregate(
        total_revenue=Sum('total_amount'),
        total_transactions=Count('id'),
        total_discount=Sum('discount')
    )
    
    # Sales by hour
    hourly_sales = []
    for hour in range(24):
        hour_sales = sales.filter(
            created_at__hour=hour
        ).aggregate(
            total=Sum('total_amount'),
            count=Count('id')
        )
        hourly_sales.append({
            'hour': f'{hour:02d}:00',
            'total': float(hour_sales['total'] or 0),
            'count': hour_sales['count'] or 0
        })
    
    # Individual transactions
    transactions = [{
        'id': s.id,
        'sale_number': s.sale_number,
        'time': s.created_at.strftime('%H:%M:%S'),
        'customer_name': s.customer_name or 'Walk-in',
        'payment_method': s.payment_method,
        'total_amount': str(s.total_amount),
        'cashier': s.cashier.username
    } for s in sales.order_by('-created_at')]
    
    return Response({
        'report_type': 'Daily Sales Report',
        'date': report_date.isoformat(),
        'summary': {
            'total_revenue': float(summary['total_revenue'] or 0),
            'total_transactions': summary['total_transactions'] or 0,
            'total_discount': float(summary['total_discount'] or 0),
            'average_transaction': float(summary['total_revenue'] or 0) / max(summary['total_transactions'] or 1, 1)
        },
        'hourly_breakdown': hourly_sales,
        'transactions': transactions
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def weekly_sales_report(request):
    """Get weekly sales summary"""
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())
    
    weekly_data = []
    total_revenue = 0
    total_transactions = 0
    
    for i in range(7):
        date = week_start + timedelta(days=i)
        daily = Sale.objects.filter(created_at__date=date).aggregate(
            total=Sum('total_amount'),
            count=Count('id')
        )
        day_total = float(daily['total'] or 0)
        day_count = daily['count'] or 0
        total_revenue += day_total
        total_transactions += day_count
        
        weekly_data.append({
            'date': date.isoformat(),
            'day_name': date.strftime('%A'),
            'total': day_total,
            'count': day_count
        })
    
    return Response({
        'report_type': 'Weekly Sales Summary',
        'week_start': week_start.isoformat(),
        'week_end': (week_start + timedelta(days=6)).isoformat(),
        'summary': {
            'total_revenue': total_revenue,
            'total_transactions': total_transactions,
            'average_daily_revenue': total_revenue / 7,
            'average_daily_transactions': total_transactions / 7
        },
        'daily_breakdown': weekly_data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def monthly_revenue_report(request):
    """Get monthly revenue analysis"""
    from sales.models import SaleItem
    
    today = timezone.now().date()
    months_data = []
    
    for i in range(12):
        # Calculate month start
        month_offset = i
        year = today.year
        month = today.month - month_offset
        while month <= 0:
            month += 12
            year -= 1
        
        month_start = today.replace(year=year, month=month, day=1)
        if month == 12:
            month_end = month_start.replace(year=year + 1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = month_start.replace(month=month + 1, day=1) - timedelta(days=1)
        
        monthly = Sale.objects.filter(
            created_at__date__gte=month_start,
            created_at__date__lte=month_end
        ).aggregate(
            total=Sum('total_amount'),
            count=Count('id')
        )
        
        # Calculate cost from sale items
        monthly_cost = SaleItem.objects.filter(
            sale__created_at__date__gte=month_start,
            sale__created_at__date__lte=month_end
        ).aggregate(
            total_cost=Sum(F('quantity') * F('product__cost_price'))
        )
        
        revenue = float(monthly['total'] or 0)
        cost = float(monthly_cost['total_cost'] or 0)
        gross_income = revenue - cost
        
        months_data.insert(0, {
            'month': month_start.strftime('%B %Y'),
            'month_short': month_start.strftime('%b'),
            'year': year,
            'total_revenue': revenue,
            'total_cost': cost,
            'gross_income': gross_income,
            'profit_margin': round((gross_income / revenue * 100), 2) if revenue > 0 else 0,
            'transaction_count': monthly['count'] or 0
        })
    
    total_revenue = sum(m['total_revenue'] for m in months_data)
    total_cost = sum(m['total_cost'] for m in months_data)
    total_gross_income = sum(m['gross_income'] for m in months_data)
    
    return Response({
        'report_type': 'Monthly Revenue Analysis',
        'period': f'{months_data[0]["month"]} - {months_data[-1]["month"]}',
        'summary': {
            'total_revenue': total_revenue,
            'total_cost': total_cost,
            'total_gross_income': total_gross_income,
            'overall_profit_margin': round((total_gross_income / total_revenue * 100), 2) if total_revenue > 0 else 0,
            'average_monthly_revenue': total_revenue / 12,
            'average_monthly_gross_income': total_gross_income / 12,
            'best_month': max(months_data, key=lambda x: x['total_revenue'])['month'],
            'best_month_revenue': max(m['total_revenue'] for m in months_data)
        },
        'monthly_breakdown': months_data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_breakdown_report(request):
    """Get payment method breakdown"""
    date_str = request.query_params.get('date')
    period = request.query_params.get('period', 'today')  # today, week, month, all
    
    today = timezone.now().date()
    
    if period == 'today':
        start_date = today
        end_date = today
    elif period == 'week':
        start_date = today - timedelta(days=7)
        end_date = today
    elif period == 'month':
        start_date = today - timedelta(days=30)
        end_date = today
    else:
        start_date = None
        end_date = None
    
    queryset = Sale.objects.all()
    if start_date and end_date:
        queryset = queryset.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )
    
    breakdown = queryset.values('payment_method').annotate(
        total=Sum('total_amount'),
        count=Count('id')
    ).order_by('-total')
    
    grand_total = sum(float(b['total'] or 0) for b in breakdown)
    
    return Response({
        'report_type': 'Payment Method Breakdown',
        'period': period,
        'start_date': start_date.isoformat() if start_date else 'All time',
        'end_date': end_date.isoformat() if end_date else 'All time',
        'summary': {
            'total_revenue': grand_total,
            'transaction_count': sum(b['count'] for b in breakdown)
        },
        'breakdown': [{
            'payment_method': b['payment_method'],
            'display_name': dict(Sale.PAYMENT_METHOD_CHOICES).get(b['payment_method'], b['payment_method']),
            'total': float(b['total'] or 0),
            'count': b['count'],
            'percentage': (float(b['total'] or 0) / grand_total * 100) if grand_total > 0 else 0
        } for b in breakdown]
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def stock_levels_report(request):
    """Get comprehensive stock levels report"""
    products = Product.objects.select_related('category').filter(is_active=True).order_by('category__name', 'name')
    
    stock_data = []
    for p in products:
        status = 'OK'
        if p.current_stock == 0:
            status = 'Out of Stock'
        elif p.current_stock <= p.minimum_stock_level:
            status = 'Low Stock'
        
        stock_data.append({
            'id': p.id,
            'name': p.name,
            'sku': p.sku,
            'category': p.category.name if p.category else 'Uncategorized',
            'current_stock': p.current_stock,
            'minimum_stock_level': p.minimum_stock_level,
            'cost_price': str(p.cost_price),
            'selling_price': str(p.selling_price),
            'stock_value': float(p.current_stock * p.cost_price),
            'status': status
        })
    
    summary = Product.objects.filter(is_active=True).aggregate(
        total_products=Count('id'),
        total_stock=Sum('current_stock'),
        total_value=Sum(F('current_stock') * F('cost_price'))
    )
    
    return Response({
        'report_type': 'Stock Levels Report',
        'generated_at': timezone.now().isoformat(),
        'summary': {
            'total_products': summary['total_products'] or 0,
            'total_stock_units': summary['total_stock'] or 0,
            'total_stock_value': float(summary['total_value'] or 0),
            'low_stock_count': len([p for p in stock_data if p['status'] == 'Low Stock']),
            'out_of_stock_count': len([p for p in stock_data if p['status'] == 'Out of Stock'])
        },
        'products': stock_data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def low_stock_report(request):
    """Get low stock alert report"""
    products = Product.objects.select_related('category').filter(
        is_active=True,
        current_stock__lte=F('minimum_stock_level')
    ).order_by('current_stock')
    
    low_stock_items = [{
        'id': p.id,
        'name': p.name,
        'sku': p.sku,
        'category': p.category.name if p.category else 'Uncategorized',
        'current_stock': p.current_stock,
        'minimum_stock_level': p.minimum_stock_level,
        'deficit': p.minimum_stock_level - p.current_stock,
        'reorder_quantity': max(p.minimum_stock_level * 2 - p.current_stock, 0),
        'cost_price': str(p.cost_price),
        'reorder_cost': float((p.minimum_stock_level * 2 - p.current_stock) * p.cost_price) if p.current_stock < p.minimum_stock_level * 2 else 0,
        'is_out_of_stock': p.current_stock == 0
    } for p in products]
    
    return Response({
        'report_type': 'Low Stock Alert Report',
        'generated_at': timezone.now().isoformat(),
        'summary': {
            'total_low_stock_items': len(low_stock_items),
            'out_of_stock_count': len([i for i in low_stock_items if i['is_out_of_stock']]),
            'total_reorder_cost': sum(i['reorder_cost'] for i in low_stock_items)
        },
        'items': low_stock_items
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def stock_movement_report(request):
    """Get stock movement history report"""
    days = int(request.query_params.get('days', 30))
    start_date = timezone.now().date() - timedelta(days=days)
    
    transactions = StockTransaction.objects.select_related(
        'product', 'performed_by'
    ).filter(
        created_at__date__gte=start_date
    ).order_by('-created_at')
    
    # Group by type
    summary = transactions.values('transaction_type').annotate(
        count=Count('id'),
        total_quantity=Sum('quantity')
    )
    
    movement_data = [{
        'id': t.id,
        'date': t.created_at.isoformat(),
        'product_name': t.product.name,
        'product_sku': t.product.sku,
        'transaction_type': t.transaction_type,
        'reason': t.reason,
        'quantity': t.quantity,
        'quantity_before': t.quantity_before,
        'quantity_after': t.quantity_after,
        'reference_number': t.reference_number or '',
        'performed_by': t.performed_by.username,
        'notes': t.notes or ''
    } for t in transactions[:500]]  # Limit to 500 records
    
    return Response({
        'report_type': 'Stock Movement History',
        'period': f'Last {days} days',
        'start_date': start_date.isoformat(),
        'end_date': timezone.now().date().isoformat(),
        'summary': {
            'total_transactions': transactions.count(),
            'by_type': {s['transaction_type']: {'count': s['count'], 'quantity': s['total_quantity']} for s in summary}
        },
        'movements': movement_data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def inventory_valuation_report(request):
    """Get inventory valuation report"""
    from inventory.models import Category
    
    products = Product.objects.select_related('category').filter(is_active=True)
    
    # Group by category
    category_data = {}
    for p in products:
        cat_name = p.category.name if p.category else 'Uncategorized'
        if cat_name not in category_data:
            category_data[cat_name] = {
                'category': cat_name,
                'product_count': 0,
                'total_units': 0,
                'cost_value': 0,
                'retail_value': 0
            }
        
        category_data[cat_name]['product_count'] += 1
        category_data[cat_name]['total_units'] += p.current_stock
        category_data[cat_name]['cost_value'] += float(p.current_stock * p.cost_price)
        category_data[cat_name]['retail_value'] += float(p.current_stock * p.selling_price)
    
    categories = list(category_data.values())
    
    total_cost = sum(c['cost_value'] for c in categories)
    total_retail = sum(c['retail_value'] for c in categories)
    
    return Response({
        'report_type': 'Inventory Valuation Report',
        'generated_at': timezone.now().isoformat(),
        'summary': {
            'total_products': products.count(),
            'total_units': sum(c['total_units'] for c in categories),
            'total_cost_value': total_cost,
            'total_retail_value': total_retail,
            'potential_profit': total_retail - total_cost,
            'average_margin_percentage': ((total_retail - total_cost) / total_cost * 100) if total_cost > 0 else 0
        },
        'by_category': sorted(categories, key=lambda x: x['cost_value'], reverse=True)
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def top_selling_report(request):
    """Get top selling products report"""
    from sales.models import SaleItem
    
    days = int(request.query_params.get('days', 30))
    limit = int(request.query_params.get('limit', 20))
    start_date = timezone.now().date() - timedelta(days=days)
    
    top_products = SaleItem.objects.filter(
        sale__created_at__date__gte=start_date
    ).values(
        'product__id',
        'product__name',
        'product__sku',
        'product__category__name'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('line_total'),
        transaction_count=Count('id')
    ).order_by('-total_revenue')[:limit]
    
    return Response({
        'report_type': 'Top Selling Products',
        'period': f'Last {days} days',
        'start_date': start_date.isoformat(),
        'end_date': timezone.now().date().isoformat(),
        'summary': {
            'total_products_sold': len(top_products),
            'total_revenue': sum(float(p['total_revenue'] or 0) for p in top_products),
            'total_units_sold': sum(p['total_quantity'] or 0 for p in top_products)
        },
        'products': [{
            'rank': i + 1,
            'id': p['product__id'],
            'name': p['product__name'],
            'sku': p['product__sku'],
            'category': p['product__category__name'] or 'Uncategorized',
            'quantity_sold': p['total_quantity'],
            'revenue': float(p['total_revenue'] or 0),
            'transaction_count': p['transaction_count']
        } for i, p in enumerate(top_products)]
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def products_by_category_report(request):
    """Get products breakdown by category"""
    from inventory.models import Category
    
    categories = Category.objects.annotate(
        product_count=Count('products', filter=Q(products__is_active=True)),
        total_stock=Sum('products__current_stock', filter=Q(products__is_active=True)),
        stock_value=Sum(
            F('products__current_stock') * F('products__cost_price'),
            filter=Q(products__is_active=True)
        )
    ).order_by('-product_count')
    
    return Response({
        'report_type': 'Products by Category',
        'generated_at': timezone.now().isoformat(),
        'summary': {
            'total_categories': categories.count(),
            'total_products': sum(c.product_count for c in categories),
            'total_stock_value': sum(float(c.stock_value or 0) for c in categories)
        },
        'categories': [{
            'id': c.id,
            'name': c.name,
            'description': c.description or '',
            'product_count': c.product_count,
            'total_stock': c.total_stock or 0,
            'stock_value': float(c.stock_value or 0)
        } for c in categories]
    })
