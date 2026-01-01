from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('stats/', views.dashboard_stats, name='stats'),
    
    # New async report endpoints
    path('reports/generate/', views.generate_report, name='generate-report'),
    path('reports/status/<str:task_id>/', views.report_status, name='report-status'),
    path('reports/download/<str:filename>/', views.download_report, name='download-report'),
    
    # Legacy JSON report endpoints (keep for CSV export)
    path('reports/daily-sales/', views.daily_sales_report, name='daily-sales-report'),
    path('reports/weekly-sales/', views.weekly_sales_report, name='weekly-sales-report'),
    path('reports/monthly-revenue/', views.monthly_revenue_report, name='monthly-revenue-report'),
    path('reports/payment-breakdown/', views.payment_breakdown_report, name='payment-breakdown-report'),
    path('reports/stock-levels/', views.stock_levels_report, name='stock-levels-report'),
    path('reports/low-stock/', views.low_stock_report, name='low-stock-report'),
    path('reports/stock-movement/', views.stock_movement_report, name='stock-movement-report'),
    path('reports/inventory-valuation/', views.inventory_valuation_report, name='inventory-valuation-report'),
    path('reports/top-selling/', views.top_selling_report, name='top-selling-report'),
    path('reports/products-by-category/', views.products_by_category_report, name='products-by-category-report'),
    # Expense reports
    path('reports/monthly-expenses/', views.monthly_expenses_report, name='monthly-expenses-report'),
    path('reports/expenses-by-category/', views.expenses_by_category_report, name='expenses-by-category-report'),
    path('reports/expenses-by-vendor/', views.expenses_by_vendor_report, name='expenses-by-vendor-report'),
    path('reports/expense-transactions/', views.expense_transactions_report, name='expense-transactions-report'),
]
