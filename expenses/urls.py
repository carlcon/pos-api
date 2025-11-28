from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'categories', views.ExpenseCategoryViewSet, basename='expense-category')
router.register(r'', views.ExpenseViewSet, basename='expense')

urlpatterns = [
    path('stats/', views.expense_stats, name='expense-stats'),
    path('', include(router.urls)),
]
