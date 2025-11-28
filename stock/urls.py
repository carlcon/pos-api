from django.urls import path
from . import views

urlpatterns = [
    path('transactions/', views.StockTransactionListView.as_view(), name='stock-transaction-list'),
    path('transactions/<int:pk>/', views.StockTransactionDetailView.as_view(), name='stock-transaction-detail'),
    path('adjust/', views.stock_adjustment, name='stock-adjustment'),
    path('low-stock/', views.low_stock_products, name='low-stock-products'),
    path('cost-history/', views.ProductCostHistoryListView.as_view(), name='cost-history-list'),
]
