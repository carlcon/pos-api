from django.urls import path
from . import views

urlpatterns = [
    path('', views.SaleListCreateView.as_view(), name='sale-list-create'),
    path('<int:pk>/', views.SaleDetailView.as_view(), name='sale-detail'),
    path('summary/', views.sales_summary, name='sales-summary'),
    path('top-products/', views.top_selling_products, name='top-selling-products'),
]
