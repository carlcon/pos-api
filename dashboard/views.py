# Dashboard views for statistics and reports
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Sum, Count, F
from django.utils import timezone
from django.http import FileResponse, Http404
from django.core.paginator import Paginator, EmptyPage
from datetime import timedelta
from decimal import Decimal
from celery.result import AsyncResult
import os

from inventory.models import Product, StoreInventory
from sales.models import Sale
from stock.models import StockTransaction
from expenses.models import Expense, ExpenseCategory
from users.mixins import require_partner_for_request, get_store_id_from_request
from .tasks import generate_report_pdf
from django.conf import settings


def paginate_data(data_list, request, data_key='data'):
    """
    Paginate data and return paginated response.
    
    Args:
        data_list: List of items to paginate
        request: Request object with page/page_size params
        data_key: Key name for data array in response (default: 'data')
    
    Returns:
        dict with pagination metadata
    """
    page_num = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 10))
    
    paginator = Paginator(data_list, page_size)
    
    try:
        page_obj = paginator.page(page_num)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    return {
        data_key: list(page_obj),
        'count': paginator.count,
        'page': page_obj.number,
        'page_size': page_size,
        'total_pages': paginator.num_pages,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
    }


def get_partner_filtered_queryset(model, request, partner_field='partner'):
    """Helper to get partner-filtered queryset for dashboard views."""
    partner = require_partner_for_request(request)
    queryset = model.objects.filter(**{partner_field: partner})
    return queryset, partner


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """
    Get comprehensive dashboard statistics.
    Store filtering is automatic when impersonating a store.
    """
    partner = require_partner_for_request(request)
    # Get store_id from query param OR effective store (impersonation/assigned)
    store_id = get_store_id_from_request(request)
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)
    
    # Base querysets filtered by partner
    sales_qs = Sale.objects.all()
    products_qs = Product.objects.all()
    if partner:
        sales_qs = sales_qs.filter(partner=partner)
        products_qs = products_qs.filter(partner=partner)
    if store_id:
        sales_qs = sales_qs.filter(store_id=store_id)
        # Note: Products are partner-level, not store-level
        # Store inventory is tracked via StockTransaction records
    
    # Today's sales
    today_sales = sales_qs.filter(created_at__date=today).aggregate(
        total=Sum('total_amount'),
        count=Count('id')
    )
    
    yesterday_sales = sales_qs.filter(created_at__date=yesterday).aggregate(
        total=Sum('total_amount')
    )
    
    today_total = float(today_sales['total'] or 0)
    yesterday_total = float(yesterday_sales['total'] or 0)
    sales_change = ((today_total - yesterday_total) / yesterday_total * 100) if yesterday_total > 0 else 0
    
    # Get store inventories
    inventory_qs = StoreInventory.objects.select_related('product').filter(product__is_active=True)
    if partner:
        inventory_qs = inventory_qs.filter(product__partner=partner)
    if store_id:
        inventory_qs = inventory_qs.filter(store_id=store_id)
    
    # Low stock items
    low_stock_inventories = inventory_qs.filter(
        current_stock__lte=F('minimum_stock_level')
    ).order_by('current_stock')[:10]
    
    # Total inventory value
    total_inventory = inventory_qs.aggregate(
        total=Sum(F('current_stock') * F('product__cost_price'))
    )
    inventory_value = float(total_inventory['total'] or 0)
    
    # Top selling products (last 30 days)
    thirty_days_ago = today - timedelta(days=30)
    from sales.models import SaleItem
    sale_items_qs = SaleItem.objects.filter(sale__created_at__gte=thirty_days_ago)
    if partner:
        sale_items_qs = sale_items_qs.filter(sale__partner=partner)
    if store_id:
        sale_items_qs = sale_items_qs.filter(sale__store_id=store_id)
    top_products = sale_items_qs.values(
        'product__id',
        'product__name',
        'product__sku'
    ).annotate(
        total_sold=Sum('quantity'),
        revenue=Sum(F('quantity') * F('unit_price'))
    ).order_by('-revenue')[:5]
    
    # Sales by payment method (today)
    payment_methods = sales_qs.filter(
        created_at__date=today
    ).values('payment_method').annotate(
        total=Sum('total_amount'),
        count=Count('id')
    )
    
    # Recent sales
    recent_sales = sales_qs.select_related('cashier').order_by('-created_at')[:10]
    
    # Weekly sales trend
    weekly_sales = []
    for i in range(7):
        date = today - timedelta(days=6-i)
        daily_sales = sales_qs.filter(created_at__date=date).aggregate(
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
        
        monthly_total = sales_qs.filter(
            created_at__date__gte=month_start,
            created_at__date__lte=month_end
        ).aggregate(total=Sum('total_amount'))
        
        monthly_revenue.insert(0, {
            'month': month_start.strftime('%b'),
            'revenue': float(monthly_total['total'] or 0)
        })
    
    # Stock summary
    stock_summary = {
        'total_products': products_qs.count(),
        'active_products': products_qs.filter(is_active=True).count(),
        'low_stock_count': inventory_qs.filter(
            current_stock__lte=F('minimum_stock_level')
        ).count(),
        'out_of_stock_count': inventory_qs.filter(current_stock=0).count()
    }
    
    return Response({
        'today_sales': {
            'total': f'{today_total:.2f}',
            'count': today_sales['count'] or 0,
            'change_percentage': round(sales_change, 2)
        },
        'low_stock_items': {
            'count': low_stock_inventories.count(),
            'items': [{
                'id': inv.product.id,
                'name': inv.product.name,
                'sku': inv.product.sku,
                'current_stock': inv.current_stock,
                'minimum_stock_level': inv.minimum_stock_level
            } for inv in low_stock_inventories]
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
    
    partner = require_partner_for_request(request)
    store_id = get_store_id_from_request(request)
    
    date_str = request.query_params.get('date', timezone.now().date().isoformat())
    try:
        report_date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        report_date = timezone.now().date()
    
    sales = Sale.objects.filter(created_at__date=report_date).select_related('cashier')
    if partner:
        sales = sales.filter(partner=partner)
    if store_id:
        sales = sales.filter(store_id=store_id)
    
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
    
    # Paginate transactions
    pagination = paginate_data(transactions, request, 'data')
    
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
        **pagination
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def weekly_sales_report(request):
    """Get weekly sales summary"""
    partner = require_partner_for_request(request)
    store_id = get_store_id_from_request(request)
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())
    
    sales_qs = Sale.objects.all()
    if partner:
        sales_qs = sales_qs.filter(partner=partner)
    if store_id:
        sales_qs = sales_qs.filter(store_id=store_id)
    
    weekly_data = []
    total_revenue = 0
    total_transactions = 0
    
    for i in range(7):
        date = week_start + timedelta(days=i)
        daily = sales_qs.filter(created_at__date=date).aggregate(
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
    
    # Paginate daily breakdown
    pagination = paginate_data(weekly_data, request, 'data')
    
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
        **pagination
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def monthly_revenue_report(request):
    """Get monthly revenue analysis"""
    from sales.models import SaleItem
    
    partner = require_partner_for_request(request)
    store_id = get_store_id_from_request(request)
    today = timezone.now().date()
    months_data = []
    
    sales_qs = Sale.objects.all()
    sale_items_qs = SaleItem.objects.all()
    if partner:
        sales_qs = sales_qs.filter(partner=partner)
        sale_items_qs = sale_items_qs.filter(sale__partner=partner)
    if store_id:
        sales_qs = sales_qs.filter(store_id=store_id)
        sale_items_qs = sale_items_qs.filter(sale__store_id=store_id)
    
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
        
        monthly = sales_qs.filter(
            created_at__date__gte=month_start,
            created_at__date__lte=month_end
        ).aggregate(
            total=Sum('total_amount'),
            count=Count('id')
        )
        
        # Calculate cost from sale items
        monthly_cost = sale_items_qs.filter(
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
    
    # Format gross_income in months_data for display
    for month in months_data:
        month['gross_income'] = f"₱{month['gross_income']:,.2f}"
    
    # Paginate monthly breakdown
    pagination = paginate_data(months_data, request, 'data')
    
    return Response({
        'report_type': 'Monthly Revenue Analysis',
        'period': f'{months_data[0]["month"]} - {months_data[-1]["month"]}',
        'summary': {
            'total_revenue': total_revenue,
            'total_cost': total_cost,
            'total_gross_income': f"₱{total_gross_income:,.2f}",
            'overall_profit_margin': round((total_gross_income / total_revenue * 100), 2) if total_revenue > 0 else 0,
            'average_monthly_revenue': total_revenue / 12,
            'average_monthly_gross_income': f"₱{(total_gross_income / 12):,.2f}",
            'best_month': max(months_data, key=lambda x: float(x['total_revenue']))['month'],
            'best_month_revenue': max(float(m['total_revenue']) for m in months_data)
        },
        **pagination
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_breakdown_report(request):
    """Get payment method breakdown"""
    partner = require_partner_for_request(request)
    store_id = get_store_id_from_request(request)
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
    if partner:
        queryset = queryset.filter(partner=partner)
    if store_id:
        queryset = queryset.filter(store_id=store_id)
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
    
    breakdown_list = [{
        'payment_method': b['payment_method'],
        'display_name': dict(Sale.PAYMENT_METHOD_CHOICES).get(b['payment_method'], b['payment_method']),
        'total': float(b['total'] or 0),
        'count': b['count'],
        'percentage': (float(b['total'] or 0) / grand_total * 100) if grand_total > 0 else 0
    } for b in breakdown]
    
    # Paginate breakdown
    pagination = paginate_data(breakdown_list, request, 'data')
    
    return Response({
        'report_type': 'Payment Method Breakdown',
        'period': period,
        'start_date': start_date.isoformat() if start_date else 'All time',
        'end_date': end_date.isoformat() if end_date else 'All time',
        'summary': {
            'total_revenue': grand_total,
            'transaction_count': sum(b['count'] for b in breakdown)
        },
        **pagination
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def stock_levels_report(request):
    """Get comprehensive stock levels report"""
    partner = require_partner_for_request(request)
    store_id = get_store_id_from_request(request)
    
    inventory_qs = StoreInventory.objects.select_related('product', 'product__category', 'store')
    if partner:
        inventory_qs = inventory_qs.filter(product__partner=partner)
    if store_id:
        inventory_qs = inventory_qs.filter(store_id=store_id)
    inventory_qs = inventory_qs.filter(product__is_active=True).order_by('product__category__name', 'product__name')
    
    stock_data = []
    for inv in inventory_qs:
        status = 'OK'
        if inv.current_stock == 0:
            status = 'Out of Stock'
        elif inv.current_stock <= inv.minimum_stock_level:
            status = 'Low Stock'
        
        stock_data.append({
            'id': inv.product.id,
            'name': inv.product.name,
            'sku': inv.product.sku,
            'category': inv.product.category.name if inv.product.category else 'Uncategorized',
            'current_stock': inv.current_stock,
            'minimum_stock_level': inv.minimum_stock_level,
            'cost_price': str(inv.product.cost_price),
            'selling_price': str(inv.product.selling_price),
            'stock_value': float(inv.current_stock * inv.product.cost_price),
            'status': status,
            'store_name': inv.store.name if inv.store else 'N/A'
        })
    
    summary = inventory_qs.aggregate(
        total_products=Count('product', distinct=True),
        total_stock=Sum('current_stock'),
        total_value=Sum(F('current_stock') * F('product__cost_price'))
    )
    
    # Paginate products
    pagination = paginate_data(stock_data, request, 'data')
    
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
        **pagination
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def low_stock_report(request):
    """Get low stock alert report"""
    partner = require_partner_for_request(request)
    store_id = get_store_id_from_request(request)
    
    inventory_qs = StoreInventory.objects.select_related('product', 'product__category', 'store').filter(
        product__is_active=True,
        current_stock__lte=F('minimum_stock_level')
    )
    if partner:
        inventory_qs = inventory_qs.filter(product__partner=partner)
    if store_id:
        inventory_qs = inventory_qs.filter(store_id=store_id)
    inventory_qs = inventory_qs.order_by('current_stock')
    
    low_stock_items = [{
        'id': inv.product.id,
        'name': inv.product.name,
        'sku': inv.product.sku,
        'category': inv.product.category.name if inv.product.category else 'Uncategorized',
        'current_stock': inv.current_stock,
        'minimum_stock_level': inv.minimum_stock_level,
        'deficit': inv.minimum_stock_level - inv.current_stock,
        'reorder_quantity': max(inv.minimum_stock_level * 2 - inv.current_stock, 0),
        'cost_price': str(inv.product.cost_price),
        'reorder_cost': float((inv.minimum_stock_level * 2 - inv.current_stock) * inv.product.cost_price) if inv.current_stock < inv.minimum_stock_level * 2 else 0,
        'is_out_of_stock': inv.current_stock == 0,
        'store_name': inv.store.name if inv.store else 'N/A'
    } for inv in inventory_qs]
    
    # Paginate items
    pagination = paginate_data(low_stock_items, request, 'data')
    
    return Response({
        'report_type': 'Low Stock Alert Report',
        'generated_at': timezone.now().isoformat(),
        'summary': {
            'total_low_stock_items': len(low_stock_items),
            'out_of_stock_count': len([i for i in low_stock_items if i['is_out_of_stock']]),
            'total_reorder_cost': sum(i['reorder_cost'] for i in low_stock_items)
        },
        **pagination
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def stock_movement_report(request):
    """Get stock movement history report"""
    partner = require_partner_for_request(request)
    store_id = get_store_id_from_request(request)
    days = int(request.query_params.get('days', 30))
    start_date = timezone.now().date() - timedelta(days=days)
    
    transactions = StockTransaction.objects.select_related(
        'product', 'performed_by'
    ).filter(
        created_at__date__gte=start_date
    )
    if partner:
        transactions = transactions.filter(partner=partner)
    if store_id:
        transactions = transactions.filter(store_id=store_id)
    transactions = transactions.order_by('-created_at')
    
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
    } for t in transactions]
    
    # Paginate movements
    pagination = paginate_data(movement_data, request, 'data')
    
    return Response({
        'report_type': 'Stock Movement History',
        'period': f'Last {days} days',
        'start_date': start_date.isoformat(),
        'end_date': timezone.now().date().isoformat(),
        'summary': {
            'total_transactions': len(movement_data),
            'by_type': {s['transaction_type']: {'count': s['count'], 'quantity': s['total_quantity']} for s in summary}
        },
        **pagination
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def inventory_valuation_report(request):
    """Get inventory valuation report"""
    from inventory.models import Category
    
    partner = require_partner_for_request(request)
    store_id = get_store_id_from_request(request)
    
    # Get store inventories instead of products directly
    inventory_qs = StoreInventory.objects.select_related('product', 'product__category').filter(
        product__is_active=True
    )
    if partner:
        inventory_qs = inventory_qs.filter(product__partner=partner)
    if store_id:
        inventory_qs = inventory_qs.filter(store_id=store_id)
    
    # Group by category
    category_data = {}
    for inv in inventory_qs:
        cat_name = inv.product.category.name if inv.product.category else 'Uncategorized'
        if cat_name not in category_data:
            category_data[cat_name] = {
                'category': cat_name,
                'product_count': 0,
                'total_units': 0,
                'cost_value': 0,
                'retail_value': 0
            }
        
        category_data[cat_name]['product_count'] += 1
        category_data[cat_name]['total_units'] += inv.current_stock
        category_data[cat_name]['cost_value'] += float(inv.current_stock * inv.product.cost_price)
        category_data[cat_name]['retail_value'] += float(inv.current_stock * inv.product.selling_price)
    
    categories = list(category_data.values())
    
    total_cost = sum(c['cost_value'] for c in categories)
    total_retail = sum(c['retail_value'] for c in categories)
    
    # Sort and paginate categories
    sorted_categories = sorted(categories, key=lambda x: x['cost_value'], reverse=True)
    pagination = paginate_data(sorted_categories, request, 'data')
    
    return Response({
        'report_type': 'Inventory Valuation Report',
        'generated_at': timezone.now().isoformat(),
        'summary': {
            'total_products': len(set(inv.product.id for inv in inventory_qs)),
            'total_units': sum(c['total_units'] for c in categories),
            'total_cost_value': total_cost,
            'total_retail_value': total_retail,
            'potential_profit': total_retail - total_cost,
            'average_margin_percentage': ((total_retail - total_cost) / total_cost * 100) if total_cost > 0 else 0
        },
        **pagination
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def top_selling_report(request):
    """Get top selling products report"""
    from sales.models import SaleItem
    
    partner = require_partner_for_request(request)
    store_id = get_store_id_from_request(request)
    days = int(request.query_params.get('days', 30))
    limit = int(request.query_params.get('limit', 20))
    start_date = timezone.now().date() - timedelta(days=days)
    
    top_products_qs = SaleItem.objects.filter(
        sale__created_at__date__gte=start_date
    )
    if partner:
        top_products_qs = top_products_qs.filter(sale__partner=partner)
    if store_id:
        top_products_qs = top_products_qs.filter(sale__store_id=store_id)
    top_products = top_products_qs.values(
        'product__id',
        'product__name',
        'product__sku',
        'product__category__name'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('line_total'),
        transaction_count=Count('id')
    ).order_by('-total_revenue')
    
    products_list = [{
        'rank': i + 1,
        'id': p['product__id'],
        'name': p['product__name'],
        'sku': p['product__sku'],
        'category': p['product__category__name'] or 'Uncategorized',
        'quantity_sold': p['total_quantity'],
        'revenue': float(p['total_revenue'] or 0),
        'transaction_count': p['transaction_count']
    } for i, p in enumerate(top_products)]
    
    # Paginate products
    pagination = paginate_data(products_list, request, 'data')
    
    return Response({
        'report_type': 'Top Selling Products',
        'period': f'Last {days} days',
        'start_date': start_date.isoformat(),
        'end_date': timezone.now().date().isoformat(),
        'summary': {
            'total_products_sold': len(products_list),
            'total_revenue': sum(p['revenue'] for p in products_list),
            'total_units_sold': sum(p['quantity_sold'] for p in products_list)
        },
        **pagination
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def products_by_category_report(request):
    """Get products breakdown by category"""
    from inventory.models import Category
    
    partner = require_partner_for_request(request)
    store_id = get_store_id_from_request(request)
    
    categories = Category.objects.all()
    if partner:
        categories = categories.filter(partner=partner)
    
    category_data = []
    for category in categories:
        # Get products in this category
        products = Product.objects.filter(category=category, is_active=True)
        if partner:
            products = products.filter(partner=partner)
        
        # Get inventory for these products
        inventory_qs = StoreInventory.objects.filter(product__in=products)
        if store_id:
            inventory_qs = inventory_qs.filter(store_id=store_id)
        
        product_count = products.count()
        total_stock = sum(inv.current_stock for inv in inventory_qs)
        stock_value = sum(float(inv.current_stock * inv.product.cost_price) for inv in inventory_qs)
        
        if product_count > 0:  # Only include categories with products
            category_data.append({
                'id': category.id,
                'name': category.name,
                'description': category.description or '',
                'product_count': product_count,
                'total_stock': total_stock,
                'stock_value': stock_value
            })
    
    # Sort by product count descending
    category_data.sort(key=lambda x: x['product_count'], reverse=True)
    
    # Paginate categories
    pagination = paginate_data(category_data, request, 'data')
    
    return Response({
        'report_type': 'Products by Category',
        'generated_at': timezone.now().isoformat(),
        'summary': {
            'total_categories': len(category_data),
            'total_products': sum(c['product_count'] for c in category_data),
            'total_stock_value': sum(c['stock_value'] for c in category_data)
        },
        **pagination
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def monthly_expenses_report(request):
    """Get monthly expenses analysis report"""
    partner = require_partner_for_request(request)
    store_id = get_store_id_from_request(request)
    today = timezone.now().date()
    months_data = []
    
    expenses_qs = Expense.objects.all()
    if partner:
        expenses_qs = expenses_qs.filter(partner=partner)
    if store_id:
        expenses_qs = expenses_qs.filter(store_id=store_id)
    
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
        
        monthly = expenses_qs.filter(
            expense_date__gte=month_start,
            expense_date__lte=month_end
        ).aggregate(
            total=Sum('amount'),
            count=Count('id')
        )
        
        months_data.insert(0, {
            'month': month_start.strftime('%B %Y'),
            'month_short': month_start.strftime('%b'),
            'year': year,
            'total_expenses': float(monthly['total'] or 0),
            'transaction_count': monthly['count'] or 0
        })
    
    total_expenses = sum(m['total_expenses'] for m in months_data)
    
    # Paginate monthly breakdown
    pagination = paginate_data(months_data, request, 'data')
    
    return Response({
        'report_type': 'Monthly Expenses Analysis',
        'period': f'{months_data[0]["month"]} - {months_data[-1]["month"]}',
        'summary': {
            'total_expenses': total_expenses,
            'average_monthly_expenses': total_expenses / 12,
            'highest_month': max(months_data, key=lambda x: x['total_expenses'])['month'],
            'highest_month_amount': max(m['total_expenses'] for m in months_data),
            'lowest_month': min(months_data, key=lambda x: x['total_expenses'])['month'],
            'lowest_month_amount': min(m['total_expenses'] for m in months_data)
        },
        **pagination
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def expenses_by_category_report(request):
    """Get expenses breakdown by category"""
    partner = require_partner_for_request(request)
    store_id = get_store_id_from_request(request)
    days = int(request.query_params.get('days', 30))
    start_date = timezone.now().date() - timedelta(days=days)
    
    expenses = Expense.objects.filter(expense_date__gte=start_date)
    if partner:
        expenses = expenses.filter(partner=partner)
    if store_id:
        expenses = expenses.filter(store_id=store_id)
    
    # By category
    by_category = expenses.values(
        'category__id',
        'category__name',
        'category__color'
    ).annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    total_amount = sum(float(c['total'] or 0) for c in by_category)
    
    categories_list = [{
        'id': c['category__id'],
        'name': c['category__name'] or 'Uncategorized',
        'color': c['category__color'] or '#6366f1',
        'total': float(c['total'] or 0),
        'count': c['count'],
        'percentage': round((float(c['total'] or 0) / total_amount * 100), 2) if total_amount > 0 else 0
    } for c in by_category]
    
    # Paginate categories
    pagination = paginate_data(categories_list, request, 'data')
    
    return Response({
        'report_type': 'Expenses by Category',
        'period': f'Last {days} days',
        'start_date': start_date.isoformat(),
        'end_date': timezone.now().date().isoformat(),
        'summary': {
            'total_expenses': total_amount,
            'total_categories': len(categories_list),
            'total_transactions': sum(c['count'] for c in categories_list)
        },
        **pagination
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def expenses_by_vendor_report(request):
    """Get expenses breakdown by vendor"""
    partner = require_partner_for_request(request)
    store_id = get_store_id_from_request(request)
    days = int(request.query_params.get('days', 30))
    start_date = timezone.now().date() - timedelta(days=days)
    
    expenses_qs = Expense.objects.filter(expense_date__gte=start_date)
    if partner:
        expenses_qs = expenses_qs.filter(partner=partner)
    if store_id:
        expenses_qs = expenses_qs.filter(store_id=store_id)
    
    by_vendor = expenses_qs.exclude(
        vendor__isnull=True
    ).exclude(
        vendor=''
    ).values('vendor').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')
    
    total_amount = sum(float(v['total'] or 0) for v in by_vendor)
    
    vendors_list = [{
        'name': v['vendor'],
        'total': float(v['total'] or 0),
        'count': v['count'],
        'percentage': round((float(v['total'] or 0) / total_amount * 100), 2) if total_amount > 0 else 0
    } for v in by_vendor]
    
    # Paginate vendors
    pagination = paginate_data(vendors_list, request, 'data')
    
    return Response({
        'report_type': 'Expenses by Vendor',
        'period': f'Last {days} days',
        'start_date': start_date.isoformat(),
        'end_date': timezone.now().date().isoformat(),
        'summary': {
            'total_expenses': total_amount,
            'total_vendors': len(vendors_list),
            'total_transactions': sum(v['count'] for v in vendors_list)
        },
        **pagination
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def expense_transactions_report(request):
    """Get detailed expense transactions report"""
    partner = require_partner_for_request(request)
    store_id = get_store_id_from_request(request)
    days = int(request.query_params.get('days', 30))
    start_date = timezone.now().date() - timedelta(days=days)
    
    expenses_qs = Expense.objects.select_related(
        'category', 'created_by'
    ).filter(
        expense_date__gte=start_date
    )
    if partner:
        expenses_qs = expenses_qs.filter(partner=partner)
    if store_id:
        expenses_qs = expenses_qs.filter(store_id=store_id)
    expenses = expenses_qs.order_by('-expense_date', '-created_at')
    
    summary_qs = Expense.objects.filter(expense_date__gte=start_date)
    if partner:
        summary_qs = summary_qs.filter(partner=partner)
    if store_id:
        summary_qs = summary_qs.filter(store_id=store_id)
    summary = summary_qs.aggregate(
        total=Sum('amount'),
        count=Count('id')
    )
    
    transactions_list = [{
        'id': e.id,
        'date': e.expense_date.isoformat(),
        'title': e.title,
        'description': e.description or '',
        'category': e.category.name if e.category else 'Uncategorized',
        'vendor': e.vendor or '-',
        'payment_method': e.get_payment_method_display(),
        'amount': float(e.amount),
        'receipt_number': e.receipt_number or '-',
        'created_by': e.created_by.username
    } for e in expenses]
    
    # Paginate transactions
    pagination = paginate_data(transactions_list, request, 'data')
    
    return Response({
        'report_type': 'Expense Transactions Report',
        'period': f'Last {days} days',
        'start_date': start_date.isoformat(),
        'end_date': timezone.now().date().isoformat(),
        'summary': {
            'total_expenses': float(summary['total'] or 0),
            'total_transactions': summary['count'] or 0,
            'average_expense': float(summary['total'] or 0) / max(summary['count'] or 1, 1)
        },
        **pagination
    })


# ============================================================================
# NEW ASYNC REPORT GENERATION ENDPOINTS
# ============================================================================

REPORT_VIEW_MAP = {
    'daily-sales': daily_sales_report,
    'weekly-sales': weekly_sales_report,
    'monthly-revenue': monthly_revenue_report,
    'payment-breakdown': payment_breakdown_report,
    'stock-levels': stock_levels_report,
    'low-stock': low_stock_report,
    'stock-movement': stock_movement_report,
    'inventory-valuation': inventory_valuation_report,
    'top-selling': top_selling_report,
    'products-by-category': products_by_category_report,
    'monthly-expenses': monthly_expenses_report,
    'expenses-by-category': expenses_by_category_report,
    'expenses-by-vendor': expenses_by_vendor_report,
    'expense-transactions': expense_transactions_report,
}


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_report(request):
    """
    Initiate async report generation.
    
    POST /api/dashboard/reports/generate/
    Body: {
        "report_type": "daily-sales",
        "format": "pdf",  # or "csv"
        "store_id": 1  # optional
    }
    
    Returns: {
        "task_id": "abc-123",
        "status": "pending"
    }
    """
    report_type = request.data.get('report_type')
    format_type = request.data.get('format', 'pdf')
    
    if report_type not in REPORT_VIEW_MAP:
        return Response({
            'error': f'Invalid report type. Valid types: {list(REPORT_VIEW_MAP.keys())}'
        }, status=400)
    
    # Get report data from existing view
    view_func = REPORT_VIEW_MAP[report_type]
    
    # Create a mock GET request using DRF's APIRequestFactory
    from rest_framework.test import APIRequestFactory
    
    factory = APIRequestFactory()
    
    # Build query params from request data
    query_params = {}
    if 'store_id' in request.data:
        query_params['store_id'] = str(request.data['store_id'])
    if 'date' in request.data:
        query_params['date'] = str(request.data['date'])
    if 'date_from' in request.data:
        query_params['date_from'] = str(request.data['date_from'])
    if 'date_to' in request.data:
        query_params['date_to'] = str(request.data['date_to'])
    if 'days' in request.data:
        query_params['days'] = str(request.data['days'])
    if 'period' in request.data:
        query_params['period'] = str(request.data['period'])
    if 'limit' in request.data:
        query_params['limit'] = str(request.data['limit'])
    if 'category_id' in request.data:
        query_params['category_id'] = str(request.data['category_id'])
    if 'vendor' in request.data:
        query_params['vendor'] = str(request.data['vendor'])
    # Don't pass pagination for PDF - get all data
    query_params['page_size'] = '1000'
    
    # Create the mock request
    query_string = '&'.join(f'{k}={v}' for k, v in query_params.items())
    mock_request = factory.get(f'/fake-endpoint/?{query_string}')
    
    # Copy auth from original request - APIRequestFactory requests work with DRF views
    mock_request.user = request.user
    # Force authentication to pass through
    mock_request._force_auth_user = request.user
    mock_request._force_auth_token = getattr(request, 'auth', None)
    
    # Get report data by calling the view function
    response = view_func(mock_request)
    # Convert to plain dict for Celery serialization
    report_data = dict(response.data)
    
    if format_type == 'csv':
        # Return data directly for CSV export (handled by frontend)
        return Response({
            'format': 'csv',
            'data': report_data
        })
    
    # For PDF, start async task
    partner_id = request.user.partner.id if hasattr(request.user, 'partner') and request.user.partner else None
    store_id = request.data.get('store_id')
    
    task = generate_report_pdf.delay(
        report_type=report_type,
        report_data=report_data,
        partner_id=partner_id,
        store_id=store_id
    )
    
    return Response({
        'task_id': task.id,
        'status': 'pending',
        'format': 'pdf'
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def report_status(request, task_id):
    """
    Check status of report generation task.
    
    GET /api/dashboard/reports/status/<task_id>/
    
    Returns: {
        "status": "pending|processing|completed|failed",
        "file_url": "...",  # if completed
        "filename": "...",   # if completed
        "error": "..."       # if failed
    }
    """
    task = AsyncResult(task_id)
    
    if task.state == 'PENDING':
        response = {
            'status': 'pending',
            'message': 'Task is waiting to start...'
        }
    elif task.state == 'PROCESSING':
        response = {
            'status': 'processing',
            'message': task.info.get('status', 'Generating report...')
        }
    elif task.state == 'SUCCESS':
        result = task.result
        file_url = f"{settings.MEDIA_URL}{result['file_path']}"
        response = {
            'status': 'completed',
            'file_url': file_url,
            'filename': result['filename'],
            'download_url': f'/api/dashboard/reports/download/{result["filename"]}/'
        }
    elif task.state == 'FAILURE':
        response = {
            'status': 'failed',
            'error': str(task.info)
        }
    else:
        response = {
            'status': task.state.lower(),
            'message': str(task.info)
        }
    
    return Response(response)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_report(request, filename):
    """
    Download generated report PDF.
    
    GET /api/dashboard/reports/download/<filename>/
    """
    # Security: ensure filename is safe
    if '..' in filename or '/' in filename:
        raise Http404("Invalid filename")
    
    file_path = os.path.join(settings.MEDIA_ROOT, 'reports', filename)
    
    if not os.path.exists(file_path):
        raise Http404("Report not found")
    
    # Optional: Add permission check to ensure user can access this report
    # For now, any authenticated user can download
    
    return FileResponse(
        open(file_path, 'rb'),
        as_attachment=True,
        filename=filename,
        content_type='application/pdf'
    )
