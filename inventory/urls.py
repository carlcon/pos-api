from django.urls import path
from . import views

urlpatterns = [
    # Categories
    path('categories/', views.CategoryListCreateView.as_view(), name='category-list-create'),
    path('categories/<int:pk>/', views.CategoryDetailView.as_view(), name='category-detail'),
    
    # Products
    path('products/', views.ProductListCreateView.as_view(), name='product-list-create'),
    path('products/<int:pk>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('products/barcode/<str:barcode>/', views.product_barcode_lookup, name='product-barcode-lookup'),
    
    # Suppliers
    path('suppliers/', views.SupplierListCreateView.as_view(), name='supplier-list-create'),
    path('suppliers/<int:pk>/', views.SupplierDetailView.as_view(), name='supplier-detail'),
    
    # Purchase Orders
    path('purchase-orders/', views.PurchaseOrderListCreateView.as_view(), name='po-list-create'),
    path('purchase-orders/<int:pk>/', views.PurchaseOrderDetailView.as_view(), name='po-detail'),
    path('purchase-orders/<int:po_id>/receive/', views.receive_po_items, name='po-receive'),
    
    # Barcode Label Printing
    path('products/<int:product_id>/print-label/', views.print_product_label, name='print-product-label'),
    path('products/print-labels/', views.print_multiple_labels, name='print-multiple-labels'),
]
