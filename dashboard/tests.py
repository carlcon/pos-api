"""
Comprehensive Unit Tests for Dashboard Module
Tests for: dashboard_stats, and all report endpoints
"""
from decimal import Decimal
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from users.models import User
from inventory.models import Category, Product
from sales.models import Sale, SaleItem
from stock.models import StockTransaction


class DashboardStatsAPITest(APITestCase):
    """Test cases for dashboard stats endpoint"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='cashier',
            password='testpass123',
            email='cashier@test.com',
            role=User.Role.CASHIER
        )
        self.category = Category.objects.create(name='Engine Parts')
        self.product = Product.objects.create(
            sku='ENG-001',
            name='Engine Oil',
            category=self.category,
            cost_price=Decimal('25.00'),
            selling_price=Decimal('35.00'),
            current_stock=100,
            minimum_stock_level=10
        )
        self.client = APIClient()
    
    def test_dashboard_stats_response(self):
        """Test dashboard stats returns expected data structure"""
        # Create some sales
        sale = Sale.objects.create(
            sale_number='SALE-001',
            payment_method='CASH',
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00'),
            cashier=self.user
        )
        SaleItem.objects.create(
            sale=sale,
            product=self.product,
            quantity=2,
            unit_price=Decimal('35.00'),
            line_total=Decimal('70.00')
        )
        
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/dashboard/stats/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check expected keys exist
        expected_keys = [
            'today_sales', 'low_stock_items', 'total_inventory_value',
            'top_selling_products', 'sales_by_payment_method',
            'recent_sales', 'weekly_sales', 'monthly_revenue', 'stock_summary'
        ]
        for key in expected_keys:
            self.assertIn(key, response.data)
    
    def test_dashboard_stats_today_sales(self):
        """Test today's sales data in dashboard stats"""
        # Create a sale
        Sale.objects.create(
            sale_number='SALE-001',
            payment_method='CASH',
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00'),
            cashier=self.user
        )
        
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/dashboard/stats/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertIn('count', response.data['today_sales'])
        self.assertIn('total', response.data['today_sales'])
    
    def test_dashboard_stats_stock_summary(self):
        """Test stock summary in dashboard stats"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/dashboard/stats/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        stock_summary = response.data['stock_summary']
        self.assertIn('total_products', stock_summary)
        self.assertIn('active_products', stock_summary)
        self.assertIn('low_stock_count', stock_summary)
        self.assertIn('out_of_stock_count', stock_summary)
    
    def test_dashboard_stats_unauthenticated(self):
        """Test unauthenticated access is denied"""
        response = self.client.get('/api/dashboard/stats/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class DailySalesReportAPITest(APITestCase):
    """Test cases for daily sales report endpoint"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='cashier',
            password='testpass123',
            email='cashier@test.com',
            role=User.Role.CASHIER
        )
        self.category = Category.objects.create(name='Engine Parts')
        self.product = Product.objects.create(
            sku='ENG-001',
            name='Engine Oil',
            category=self.category,
            cost_price=Decimal('25.00'),
            selling_price=Decimal('35.00'),
            current_stock=100
        )
        # Create some sales
        self.sale1 = Sale.objects.create(
            sale_number='SALE-001',
            payment_method='CASH',
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00'),
            cashier=self.user
        )
        self.sale2 = Sale.objects.create(
            sale_number='SALE-002',
            payment_method='CARD',
            subtotal=Decimal('150.00'),
            total_amount=Decimal('150.00'),
            cashier=self.user
        )
        self.client = APIClient()
    
    def test_daily_sales_report(self):
        """Test daily sales report returns correct data"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/dashboard/reports/daily-sales/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertEqual(response.data['report_type'], 'Daily Sales Report')
        self.assertIn('summary', response.data)
        self.assertIn('hourly_breakdown', response.data)
        self.assertIn('transactions', response.data)
    
    def test_daily_sales_report_with_date(self):
        """Test daily sales report with specific date"""
        self.client.force_authenticate(user=self.user)
        today = timezone.now().date().isoformat()
        response = self.client.get(f'/api/dashboard/reports/daily-sales/?date={today}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['date'], today)
    
    def test_daily_sales_summary_totals(self):
        """Test daily sales summary contains correct totals"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/dashboard/reports/daily-sales/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        summary = response.data['summary']
        self.assertIn('total_revenue', summary)
        self.assertIn('total_transactions', summary)
        self.assertIn('total_discount', summary)
        self.assertIn('average_transaction', summary)


class WeeklySalesReportAPITest(APITestCase):
    """Test cases for weekly sales report endpoint"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='cashier',
            password='testpass123',
            email='cashier@test.com',
            role=User.Role.CASHIER
        )
        Sale.objects.create(
            sale_number='SALE-001',
            payment_method='CASH',
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00'),
            cashier=self.user
        )
        self.client = APIClient()
    
    def test_weekly_sales_report(self):
        """Test weekly sales report returns correct data"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/dashboard/reports/weekly-sales/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertEqual(response.data['report_type'], 'Weekly Sales Summary')
        self.assertIn('week_start', response.data)
        self.assertIn('week_end', response.data)
        self.assertIn('summary', response.data)
        self.assertIn('daily_breakdown', response.data)
    
    def test_weekly_sales_has_seven_days(self):
        """Test weekly sales report has 7 days of data"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/dashboard/reports/weekly-sales/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertEqual(len(response.data['daily_breakdown']), 7)


class MonthlyRevenueReportAPITest(APITestCase):
    """Test cases for monthly revenue report endpoint"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='cashier',
            password='testpass123',
            email='cashier@test.com',
            role=User.Role.CASHIER
        )
        Sale.objects.create(
            sale_number='SALE-001',
            payment_method='CASH',
            subtotal=Decimal('500.00'),
            total_amount=Decimal('500.00'),
            cashier=self.user
        )
        self.client = APIClient()
    
    def test_monthly_revenue_report(self):
        """Test monthly revenue report returns correct data"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/dashboard/reports/monthly-revenue/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertEqual(response.data['report_type'], 'Monthly Revenue Analysis')
        self.assertIn('period', response.data)
        self.assertIn('summary', response.data)
        self.assertIn('monthly_breakdown', response.data)
    
    def test_monthly_revenue_has_twelve_months(self):
        """Test monthly revenue report has 12 months of data"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/dashboard/reports/monthly-revenue/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertEqual(len(response.data['monthly_breakdown']), 12)


class PaymentBreakdownReportAPITest(APITestCase):
    """Test cases for payment breakdown report endpoint"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='cashier',
            password='testpass123',
            email='cashier@test.com',
            role=User.Role.CASHIER
        )
        # Create sales with different payment methods
        Sale.objects.create(
            sale_number='SALE-CASH',
            payment_method='CASH',
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00'),
            cashier=self.user
        )
        Sale.objects.create(
            sale_number='SALE-CARD',
            payment_method='CARD',
            subtotal=Decimal('200.00'),
            total_amount=Decimal('200.00'),
            cashier=self.user
        )
        self.client = APIClient()
    
    def test_payment_breakdown_report(self):
        """Test payment breakdown report returns correct data"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/dashboard/reports/payment-breakdown/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertEqual(response.data['report_type'], 'Payment Method Breakdown')
        self.assertIn('summary', response.data)
        self.assertIn('breakdown', response.data)
    
    def test_payment_breakdown_periods(self):
        """Test payment breakdown with different periods"""
        self.client.force_authenticate(user=self.user)
        periods = ['today', 'week', 'month', 'all']
        for period in periods:
            response = self.client.get(f'/api/dashboard/reports/payment-breakdown/?period={period}')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['period'], period)


class StockLevelsReportAPITest(APITestCase):
    """Test cases for stock levels report endpoint"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='cashier',
            password='testpass123',
            email='cashier@test.com',
            role=User.Role.CASHIER
        )
        self.category = Category.objects.create(name='Engine Parts')
        self.product1 = Product.objects.create(
            sku='ENG-001',
            name='Engine Oil',
            category=self.category,
            cost_price=Decimal('25.00'),
            selling_price=Decimal('35.00'),
            current_stock=100,
            minimum_stock_level=10,
            is_active=True
        )
        self.product2 = Product.objects.create(
            sku='ENG-002',
            name='Brake Fluid',
            category=self.category,
            cost_price=Decimal('15.00'),
            selling_price=Decimal('25.00'),
            current_stock=5,  # Low stock
            minimum_stock_level=10,
            is_active=True
        )
        self.product3 = Product.objects.create(
            sku='ENG-003',
            name='Coolant',
            category=self.category,
            cost_price=Decimal('10.00'),
            selling_price=Decimal('18.00'),
            current_stock=0,  # Out of stock
            minimum_stock_level=5,
            is_active=True
        )
        self.client = APIClient()
    
    def test_stock_levels_report(self):
        """Test stock levels report returns correct data"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/dashboard/reports/stock-levels/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertEqual(response.data['report_type'], 'Stock Levels Report')
        self.assertIn('summary', response.data)
        self.assertIn('products', response.data)
    
    def test_stock_levels_summary(self):
        """Test stock levels summary contains expected fields"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/dashboard/reports/stock-levels/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        summary = response.data['summary']
        self.assertIn('total_products', summary)
        self.assertIn('total_stock_units', summary)
        self.assertIn('total_stock_value', summary)
        self.assertIn('low_stock_count', summary)
        self.assertIn('out_of_stock_count', summary)


class LowStockReportAPITest(APITestCase):
    """Test cases for low stock report endpoint"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='cashier',
            password='testpass123',
            email='cashier@test.com',
            role=User.Role.CASHIER
        )
        self.category = Category.objects.create(name='Engine Parts')
        self.low_stock_product = Product.objects.create(
            sku='ENG-001',
            name='Engine Oil',
            category=self.category,
            cost_price=Decimal('25.00'),
            selling_price=Decimal('35.00'),
            current_stock=3,
            minimum_stock_level=10,
            is_active=True
        )
        self.client = APIClient()
    
    def test_low_stock_report(self):
        """Test low stock report returns correct data"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/dashboard/reports/low-stock/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertEqual(response.data['report_type'], 'Low Stock Alert Report')
        self.assertIn('summary', response.data)
        self.assertIn('items', response.data)
    
    def test_low_stock_item_details(self):
        """Test low stock items contain expected details"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/dashboard/reports/low-stock/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertTrue(len(response.data['items']) > 0)
        item = response.data['items'][0]
        self.assertIn('deficit', item)
        self.assertIn('reorder_quantity', item)
        self.assertIn('reorder_cost', item)


class StockMovementReportAPITest(APITestCase):
    """Test cases for stock movement report endpoint"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='inventory_staff',
            password='testpass123',
            email='staff@test.com',
            role=User.Role.INVENTORY_STAFF
        )
        self.category = Category.objects.create(name='Engine Parts')
        self.product = Product.objects.create(
            sku='ENG-001',
            name='Engine Oil',
            category=self.category,
            cost_price=Decimal('25.00'),
            selling_price=Decimal('35.00'),
            current_stock=100
        )
        # Create stock transactions
        StockTransaction.objects.create(
            product=self.product,
            transaction_type='IN',
            reason='PURCHASE',
            quantity=50,
            quantity_before=50,
            quantity_after=100,
            performed_by=self.user
        )
        StockTransaction.objects.create(
            product=self.product,
            transaction_type='OUT',
            reason='SALE',
            quantity=10,
            quantity_before=100,
            quantity_after=90,
            performed_by=self.user
        )
        self.client = APIClient()
    
    def test_stock_movement_report(self):
        """Test stock movement report returns correct data"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/dashboard/reports/stock-movement/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertEqual(response.data['report_type'], 'Stock Movement History')
        self.assertIn('summary', response.data)
        self.assertIn('movements', response.data)
    
    def test_stock_movement_with_days_filter(self):
        """Test stock movement report with days filter"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/dashboard/reports/stock-movement/?days=7')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['period'], 'Last 7 days')


class InventoryValuationReportAPITest(APITestCase):
    """Test cases for inventory valuation report endpoint"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='cashier',
            password='testpass123',
            email='cashier@test.com',
            role=User.Role.CASHIER
        )
        self.category1 = Category.objects.create(name='Engine Parts')
        self.category2 = Category.objects.create(name='Electrical')
        Product.objects.create(
            sku='ENG-001',
            name='Engine Oil',
            category=self.category1,
            cost_price=Decimal('25.00'),
            selling_price=Decimal('35.00'),
            current_stock=100,
            is_active=True
        )
        Product.objects.create(
            sku='ELE-001',
            name='Battery',
            category=self.category2,
            cost_price=Decimal('80.00'),
            selling_price=Decimal('120.00'),
            current_stock=20,
            is_active=True
        )
        self.client = APIClient()
    
    def test_inventory_valuation_report(self):
        """Test inventory valuation report returns correct data"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/dashboard/reports/inventory-valuation/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertEqual(response.data['report_type'], 'Inventory Valuation Report')
        self.assertIn('summary', response.data)
        self.assertIn('by_category', response.data)
    
    def test_inventory_valuation_summary(self):
        """Test inventory valuation summary"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/dashboard/reports/inventory-valuation/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        summary = response.data['summary']
        self.assertIn('total_products', summary)
        self.assertIn('total_units', summary)
        self.assertIn('total_cost_value', summary)
        self.assertIn('total_retail_value', summary)
        self.assertIn('potential_profit', summary)


class TopSellingReportAPITest(APITestCase):
    """Test cases for top selling products report endpoint"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='cashier',
            password='testpass123',
            email='cashier@test.com',
            role=User.Role.CASHIER
        )
        self.category = Category.objects.create(name='Engine Parts')
        self.product = Product.objects.create(
            sku='ENG-001',
            name='Engine Oil',
            category=self.category,
            cost_price=Decimal('25.00'),
            selling_price=Decimal('35.00'),
            current_stock=100
        )
        # Create sales
        sale = Sale.objects.create(
            sale_number='SALE-001',
            payment_method='CASH',
            subtotal=Decimal('175.00'),
            total_amount=Decimal('175.00'),
            cashier=self.user
        )
        SaleItem.objects.create(
            sale=sale,
            product=self.product,
            quantity=5,
            unit_price=Decimal('35.00'),
            line_total=Decimal('175.00')
        )
        self.client = APIClient()
    
    def test_top_selling_report(self):
        """Test top selling report returns correct data"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/dashboard/reports/top-selling/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertEqual(response.data['report_type'], 'Top Selling Products')
        self.assertIn('summary', response.data)
        self.assertIn('products', response.data)
    
    def test_top_selling_with_limit(self):
        """Test top selling report with limit parameter"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/dashboard/reports/top-selling/?limit=5')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(response.data['products']), 5)


class ProductsByCategoryReportAPITest(APITestCase):
    """Test cases for products by category report endpoint"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='cashier',
            password='testpass123',
            email='cashier@test.com',
            role=User.Role.CASHIER
        )
        self.category1 = Category.objects.create(name='Engine Parts')
        self.category2 = Category.objects.create(name='Electrical')
        Product.objects.create(
            sku='ENG-001',
            name='Engine Oil',
            category=self.category1,
            cost_price=Decimal('25.00'),
            selling_price=Decimal('35.00'),
            current_stock=100,
            is_active=True
        )
        Product.objects.create(
            sku='ENG-002',
            name='Brake Fluid',
            category=self.category1,
            cost_price=Decimal('15.00'),
            selling_price=Decimal('25.00'),
            current_stock=50,
            is_active=True
        )
        Product.objects.create(
            sku='ELE-001',
            name='Battery',
            category=self.category2,
            cost_price=Decimal('80.00'),
            selling_price=Decimal('120.00'),
            current_stock=20,
            is_active=True
        )
        self.client = APIClient()
    
    def test_products_by_category_report(self):
        """Test products by category report returns correct data"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/dashboard/reports/products-by-category/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertEqual(response.data['report_type'], 'Products by Category')
        self.assertIn('summary', response.data)
        self.assertIn('categories', response.data)
    
    def test_products_by_category_structure(self):
        """Test products by category has expected category structure"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/dashboard/reports/products-by-category/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertTrue(len(response.data['categories']) >= 2)
        category = response.data['categories'][0]
        self.assertIn('id', category)
        self.assertIn('name', category)
        self.assertIn('product_count', category)
        self.assertIn('total_stock', category)
        self.assertIn('stock_value', category)
