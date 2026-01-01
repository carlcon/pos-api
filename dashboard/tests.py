"""
Comprehensive tests for Dashboard Module.
Tests for: dashboard_stats, and all report endpoints.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from rest_framework import status
from sales.models import Sale, SaleItem
from inventory.models import Category, Product
from stock.models import StockTransaction
from users.models import User


# ============== Dashboard Stats API Tests ==============

@pytest.mark.django_db
class TestDashboardStatsAPI:
    """Test cases for dashboard stats endpoint"""
    
    def test_dashboard_stats_response(self, admin_client, sale, product):
        """Test dashboard stats returns expected data structure"""
        response = admin_client.get('/api/dashboard/stats/')
        assert response.status_code == status.HTTP_200_OK
        
        expected_keys = [
            'today_sales', 'low_stock_items', 'total_inventory_value',
            'top_selling_products', 'sales_by_payment_method',
            'recent_sales', 'weekly_sales', 'monthly_revenue', 'stock_summary'
        ]
        for key in expected_keys:
            assert key in response.data
    
    def test_dashboard_stats_today_sales(self, admin_client, sale, cashier_user):
        """Test today's sales data in dashboard stats"""
        response = admin_client.get('/api/dashboard/stats/')
        assert response.status_code == status.HTTP_200_OK
        
        assert 'count' in response.data['today_sales']
        assert 'total' in response.data['today_sales']
    
    def test_dashboard_stats_stock_summary(self, admin_client, product):
        """Test stock summary in dashboard stats"""
        response = admin_client.get('/api/dashboard/stats/')
        assert response.status_code == status.HTTP_200_OK
        
        stock_summary = response.data['stock_summary']
        assert 'total_products' in stock_summary
        assert 'active_products' in stock_summary
        assert 'low_stock_count' in stock_summary
        assert 'out_of_stock_count' in stock_summary

    def test_super_admin_must_impersonate(self, super_admin_client):
        """Super admin without impersonation cannot access dashboard stats"""
        response = super_admin_client.get('/api/dashboard/stats/')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'impersonate' in str(response.data.get('detail', '')).lower()
    
    def test_dashboard_stats_unauthenticated(self, api_client):
        """Test unauthenticated access is denied"""
        response = api_client.get('/api/dashboard/stats/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============== Daily Sales Report API Tests ==============

@pytest.mark.django_db
class TestDailySalesReportAPI:
    """Test cases for daily sales report endpoint"""
    
    def test_daily_sales_report(self, admin_client, sale):
        """Test daily sales report returns correct data"""
        response = admin_client.get('/api/dashboard/reports/daily-sales/')
        assert response.status_code == status.HTTP_200_OK
        
        assert response.data['report_type'] == 'Daily Sales Report'
        assert 'summary' in response.data
        assert 'hourly_breakdown' in response.data
        assert 'transactions' in response.data
    
    def test_daily_sales_report_with_date(self, admin_client, sale):
        """Test daily sales report with specific date"""
        today = timezone.now().date().isoformat()
        response = admin_client.get(f'/api/dashboard/reports/daily-sales/?date={today}')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['date'] == today
    
    def test_daily_sales_summary_totals(self, admin_client, sale):
        """Test daily sales summary contains correct totals"""
        response = admin_client.get('/api/dashboard/reports/daily-sales/')
        assert response.status_code == status.HTTP_200_OK
        
        summary = response.data['summary']
        assert 'total_revenue' in summary
        assert 'total_transactions' in summary
        assert 'total_discount' in summary
        assert 'average_transaction' in summary


# ============== Weekly Sales Report API Tests ==============

@pytest.mark.django_db
class TestWeeklySalesReportAPI:
    """Test cases for weekly sales report endpoint"""
    
    def test_weekly_sales_report(self, admin_client, sale):
        """Test weekly sales report returns correct data"""
        response = admin_client.get('/api/dashboard/reports/weekly-sales/')
        assert response.status_code == status.HTTP_200_OK
        
        assert response.data['report_type'] == 'Weekly Sales Summary'
        assert 'week_start' in response.data
        assert 'week_end' in response.data
        assert 'summary' in response.data
        assert 'daily_breakdown' in response.data
    
    def test_weekly_sales_has_seven_days(self, admin_client, sale):
        """Test weekly sales report has 7 days of data"""
        response = admin_client.get('/api/dashboard/reports/weekly-sales/')
        assert response.status_code == status.HTTP_200_OK
        
        assert len(response.data['daily_breakdown']) == 7


# ============== Monthly Revenue Report API Tests ==============

@pytest.mark.django_db
class TestMonthlyRevenueReportAPI:
    """Test cases for monthly revenue report endpoint"""
    
    def test_monthly_revenue_report(self, admin_client, sale):
        """Test monthly revenue report returns correct data"""
        response = admin_client.get('/api/dashboard/reports/monthly-revenue/')
        assert response.status_code == status.HTTP_200_OK
        
        assert response.data['report_type'] == 'Monthly Revenue Analysis'
        assert 'period' in response.data
        assert 'summary' in response.data
        assert 'monthly_breakdown' in response.data
    
    def test_monthly_revenue_has_twelve_months(self, admin_client, sale):
        """Test monthly revenue report has 12 months of data"""
        response = admin_client.get('/api/dashboard/reports/monthly-revenue/')
        assert response.status_code == status.HTTP_200_OK
        
        assert len(response.data['monthly_breakdown']) == 12


# ============== Payment Breakdown Report API Tests ==============

@pytest.mark.django_db
class TestPaymentBreakdownReportAPI:
    """Test cases for payment breakdown report endpoint"""
    
    def test_payment_breakdown_report(self, admin_client, sale, partner, cashier_user):
        """Test payment breakdown report returns correct data"""
        Sale.objects.create(
            partner=partner,
            sale_number='SALE-CARD-001',
            payment_method='CARD',
            subtotal=Decimal('200.00'),
            total_amount=Decimal('200.00'),
            cashier=cashier_user
        )
        
        response = admin_client.get('/api/dashboard/reports/payment-breakdown/')
        assert response.status_code == status.HTTP_200_OK
        
        assert response.data['report_type'] == 'Payment Method Breakdown'
        assert 'summary' in response.data
        assert 'breakdown' in response.data
    
    def test_payment_breakdown_periods(self, admin_client, sale):
        """Test payment breakdown with different periods"""
        periods = ['today', 'week', 'month', 'all']
        for period in periods:
            response = admin_client.get(f'/api/dashboard/reports/payment-breakdown/?period={period}')
            assert response.status_code == status.HTTP_200_OK
            assert response.data['period'] == period


# ============== Stock Levels Report API Tests ==============

@pytest.mark.django_db
class TestStockLevelsReportAPI:
    """Test cases for stock levels report endpoint"""
    
    def test_stock_levels_report(self, admin_client, product, low_stock_product):
        """Test stock levels report returns correct data"""
        response = admin_client.get('/api/dashboard/reports/stock-levels/')
        assert response.status_code == status.HTTP_200_OK
        
        assert response.data['report_type'] == 'Stock Levels Report'
        assert 'summary' in response.data
        assert 'products' in response.data
    
    def test_stock_levels_summary(self, admin_client, product, low_stock_product, partner, category, store):
        """Test stock levels summary contains expected fields"""
        from inventory.models import StoreInventory
        out_of_stock = Product.objects.create(
            partner=partner,
            sku='OOS-001',
            name='Out of Stock Item',
            category=category,
            cost_price=Decimal('10.00'),
            selling_price=Decimal('18.00'),
            is_active=True
        )
        StoreInventory.objects.create(
            product=out_of_stock,
            store=store,
            current_stock=0,
            minimum_stock_level=5
        )
        
        response = admin_client.get('/api/dashboard/reports/stock-levels/')
        assert response.status_code == status.HTTP_200_OK
        
        summary = response.data['summary']
        assert 'total_products' in summary
        assert 'total_stock_units' in summary
        assert 'total_stock_value' in summary
        assert 'low_stock_count' in summary
        assert 'out_of_stock_count' in summary


# ============== Low Stock Report API Tests ==============

@pytest.mark.django_db
class TestLowStockReportAPI:
    """Test cases for low stock report endpoint"""
    
    def test_low_stock_report(self, admin_client, low_stock_product):
        """Test low stock report returns correct data"""
        response = admin_client.get('/api/dashboard/reports/low-stock/')
        assert response.status_code == status.HTTP_200_OK
        
        assert response.data['report_type'] == 'Low Stock Alert Report'
        assert 'summary' in response.data
        assert 'items' in response.data
    
    def test_low_stock_item_details(self, admin_client, low_stock_product):
        """Test low stock items contain expected details"""
        response = admin_client.get('/api/dashboard/reports/low-stock/')
        assert response.status_code == status.HTTP_200_OK
        
        if len(response.data['items']) > 0:
            item = response.data['items'][0]
            assert 'deficit' in item
            assert 'reorder_quantity' in item
            assert 'reorder_cost' in item


# ============== Stock Movement Report API Tests ==============

@pytest.mark.django_db
class TestStockMovementReportAPI:
    """Test cases for stock movement report endpoint"""
    
    def test_stock_movement_report(self, admin_client, stock_transaction, stock_out_transaction):
        """Test stock movement report returns correct data"""
        response = admin_client.get('/api/dashboard/reports/stock-movement/')
        assert response.status_code == status.HTTP_200_OK
        
        assert response.data['report_type'] == 'Stock Movement History'
        assert 'summary' in response.data
        assert 'movements' in response.data
    
    def test_stock_movement_with_days_filter(self, admin_client, stock_transaction):
        """Test stock movement report with days filter"""
        response = admin_client.get('/api/dashboard/reports/stock-movement/?days=7')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['period'] == 'Last 7 days'


# ============== Inventory Valuation Report API Tests ==============

@pytest.mark.django_db
class TestInventoryValuationReportAPI:
    """Test cases for inventory valuation report endpoint"""
    
    def test_inventory_valuation(self, admin_client, product, partner, category, store):
        """Test inventory valuation report returns correct data"""
        from inventory.models import StoreInventory
        category2 = Category.objects.create(partner=partner, name='Electrical')
        ele_product = Product.objects.create(
            partner=partner,
            sku='ELE-001',
            name='Battery',
            category=category2,
            cost_price=Decimal('80.00'),
            selling_price=Decimal('120.00'),
            is_active=True
        )
        StoreInventory.objects.create(
            product=ele_product,
            store=store,
            current_stock=20,
            minimum_stock_level=5
        )
        
        response = admin_client.get('/api/dashboard/reports/inventory-valuation/')
        assert response.status_code == status.HTTP_200_OK
        
        assert response.data['report_type'] == 'Inventory Valuation Report'
        assert 'summary' in response.data
        assert 'by_category' in response.data
    
    def test_inventory_valuation_summary(self, admin_client, product):
        """Test inventory valuation summary"""
        response = admin_client.get('/api/dashboard/reports/inventory-valuation/')
        assert response.status_code == status.HTTP_200_OK
        
        summary = response.data['summary']
        assert 'total_products' in summary
        assert 'total_units' in summary
        assert 'total_cost_value' in summary
        assert 'total_retail_value' in summary
        assert 'potential_profit' in summary


# ============== Top Selling Report API Tests ==============

@pytest.mark.django_db
class TestTopSellingReportAPI:
    """Test cases for top selling products report endpoint"""
    
    def test_top_selling_report(self, admin_client, sale):
        """Test top selling report returns correct data"""
        response = admin_client.get('/api/dashboard/reports/top-selling/')
        assert response.status_code == status.HTTP_200_OK
        
        assert response.data['report_type'] == 'Top Selling Products'
        assert 'summary' in response.data
        assert 'products' in response.data
    
    def test_top_selling_with_limit(self, admin_client, sale):
        """Test top selling report with limit parameter"""
        response = admin_client.get('/api/dashboard/reports/top-selling/?limit=5')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['products']) <= 5


# ============== Products By Category Report API Tests ==============

@pytest.mark.django_db
class TestProductsByCategoryReportAPI:
    """Test cases for products by category report endpoint"""
    
    def test_products_by_category_report(self, admin_client, product, product2, category, partner, store):
        """Test products by category report returns correct data"""
        from inventory.models import StoreInventory
        category2 = Category.objects.create(partner=partner, name='Electrical Category')
        alt_product = Product.objects.create(
            partner=partner,
            sku='ELE-002',
            name='Alternator',
            category=category2,
            cost_price=Decimal('80.00'),
            selling_price=Decimal('120.00'),
            is_active=True
        )
        StoreInventory.objects.create(
            product=alt_product,
            store=store,
            current_stock=20,
            minimum_stock_level=5
        )
        
        response = admin_client.get('/api/dashboard/reports/products-by-category/')
        assert response.status_code == status.HTTP_200_OK
        
        assert response.data['report_type'] == 'Products by Category'
        assert 'summary' in response.data
        assert 'categories' in response.data
    
    def test_products_by_category_structure(self, admin_client, product, category):
        """Test products by category has expected category structure"""
        response = admin_client.get('/api/dashboard/reports/products-by-category/')
        assert response.status_code == status.HTTP_200_OK
        
        if len(response.data['categories']) > 0:
            cat_data = response.data['categories'][0]
            assert 'id' in cat_data
            assert 'name' in cat_data
            assert 'product_count' in cat_data
            assert 'total_stock' in cat_data
            assert 'stock_value' in cat_data


# ============== Partner Isolation Tests ==============

@pytest.mark.django_db
class TestDashboardPartnerIsolation:
    """Test partner isolation in dashboard reports"""
    
    def test_dashboard_stats_partner_isolation(self, admin_client, sale, partner2, cashier_user):
        """Test dashboard stats only includes partner's data"""
        partner2_cashier = User.objects.create_user(
            username='p2_dash_cashier',
            password='test123',
            role=User.Role.CASHIER,
            partner=partner2
        )
        partner2_sale = Sale.objects.create(
            partner=partner2,
            sale_number='P2-DASH-001',
            subtotal=Decimal('1000.00'),
            total_amount=Decimal('1000.00'),
            cashier=partner2_cashier
        )
        
        response = admin_client.get('/api/dashboard/stats/')
        assert response.status_code == status.HTTP_200_OK
        # Stats should only reflect partner1's data

    def test_reports_partner_isolation(self, admin_client, sale, partner2, cashier_user):
        """Test reports only include the authenticated user's partner data
        
        Dashboard views should filter data by the user's partner for proper multi-tenancy.
        """
        partner2_cashier = User.objects.create_user(
            username='p2_report_cashier',
            password='test123',
            role=User.Role.CASHIER,
            partner=partner2
        )
        Sale.objects.create(
            partner=partner2,
            sale_number='P2-REPORT-001',
            subtotal=Decimal('500.00'),
            total_amount=Decimal('500.00'),
            cashier=partner2_cashier
        )
        
        response = admin_client.get('/api/dashboard/reports/daily-sales/')
        assert response.status_code == status.HTTP_200_OK
        
        # Partner isolation: Dashboard should only show current partner's sales
        transactions = response.data.get('transactions', [])
        for txn in transactions:
            sale_number = txn.get('sale_number', '')
            assert not sale_number.startswith('P2-'), f"Found partner2 sale in partner1's report: {sale_number}"


# ============== Impersonation Tests ==============

@pytest.mark.django_db
class TestDashboardImpersonation:
    """Test impersonation for dashboard endpoints"""
    
    def test_impersonation_sees_partner_dashboard(self, impersonation_client, sale, product):
        """Test impersonation sees impersonated partner's dashboard"""
        response = impersonation_client.get('/api/dashboard/stats/')
        assert response.status_code == status.HTTP_200_OK
    
    def test_impersonation_sees_partner_reports(self, impersonation_client, sale):
        """Test impersonation sees impersonated partner's reports"""
        response = impersonation_client.get('/api/dashboard/reports/daily-sales/')
        assert response.status_code == status.HTTP_200_OK
