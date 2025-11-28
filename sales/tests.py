"""
Comprehensive Unit Tests for Sales Module
Tests for: Sale, SaleItem models, SaleCreateSerializer, SaleListCreateView, SaleDetailView
"""
from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from users.models import User
from inventory.models import Category, Product
from sales.models import Sale, SaleItem
from sales.serializers import SaleSerializer, SaleCreateSerializer
from stock.models import StockTransaction


class SaleModelTest(TestCase):
    """Test cases for Sale model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='cashier',
            password='testpass123',
            email='cashier@test.com',
            role=User.Role.CASHIER
        )
        self.sale = Sale.objects.create(
            sale_number='SALE-001',
            customer_name='John Doe',
            payment_method='CASH',
            subtotal=Decimal('100.00'),
            discount=Decimal('10.00'),
            total_amount=Decimal('90.00'),
            cashier=self.user
        )
    
    def test_sale_creation(self):
        """Test sale is created correctly"""
        self.assertEqual(self.sale.sale_number, 'SALE-001')
        self.assertEqual(self.sale.customer_name, 'John Doe')
        self.assertEqual(self.sale.payment_method, 'CASH')
        self.assertEqual(self.sale.total_amount, Decimal('90.00'))
        self.assertEqual(self.sale.cashier, self.user)
    
    def test_sale_str_representation(self):
        """Test sale string representation"""
        expected = f"Sale-{self.sale.sale_number} - {self.sale.total_amount}"
        self.assertEqual(str(self.sale), expected)
    
    def test_sale_payment_method_choices(self):
        """Test all payment method choices"""
        payment_methods = ['CASH', 'CARD', 'BANK_TRANSFER', 'CHECK', 'CREDIT']
        for method in payment_methods:
            sale = Sale.objects.create(
                sale_number=f'SALE-{method}',
                payment_method=method,
                subtotal=Decimal('50.00'),
                total_amount=Decimal('50.00'),
                cashier=self.user
            )
            self.assertEqual(sale.payment_method, method)
    
    def test_sale_without_customer_name(self):
        """Test sale can be created without customer name (walk-in)"""
        sale = Sale.objects.create(
            sale_number='SALE-WALKIN',
            payment_method='CASH',
            subtotal=Decimal('50.00'),
            total_amount=Decimal('50.00'),
            cashier=self.user
        )
        self.assertIsNone(sale.customer_name)
    
    def test_sale_discount_default(self):
        """Test sale discount defaults to zero"""
        sale = Sale.objects.create(
            sale_number='SALE-NO-DISC',
            payment_method='CASH',
            subtotal=Decimal('50.00'),
            total_amount=Decimal('50.00'),
            cashier=self.user
        )
        self.assertEqual(sale.discount, Decimal('0.00'))


class SaleItemModelTest(TestCase):
    """Test cases for SaleItem model"""
    
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
        self.sale = Sale.objects.create(
            sale_number='SALE-001',
            payment_method='CASH',
            subtotal=Decimal('70.00'),
            total_amount=Decimal('70.00'),
            cashier=self.user
        )
        self.sale_item = SaleItem.objects.create(
            sale=self.sale,
            product=self.product,
            quantity=2,
            unit_price=Decimal('35.00'),
            discount=Decimal('0.00'),
            line_total=Decimal('70.00')
        )
    
    def test_sale_item_creation(self):
        """Test sale item is created correctly"""
        self.assertEqual(self.sale_item.sale, self.sale)
        self.assertEqual(self.sale_item.product, self.product)
        self.assertEqual(self.sale_item.quantity, 2)
        self.assertEqual(self.sale_item.unit_price, Decimal('35.00'))
        self.assertEqual(self.sale_item.line_total, Decimal('70.00'))
    
    def test_sale_item_str_representation(self):
        """Test sale item string representation"""
        self.assertIn(self.product.name, str(self.sale_item))
    
    def test_sale_item_with_discount(self):
        """Test sale item with discount applied"""
        # Need a different product due to unique constraint on (sale, product)
        product2 = Product.objects.create(
            sku='ENG-002',
            name='Brake Fluid',
            category=self.category,
            cost_price=Decimal('15.00'),
            selling_price=Decimal('25.00'),
            current_stock=50
        )
        sale_item = SaleItem.objects.create(
            sale=self.sale,
            product=product2,
            quantity=2,
            unit_price=Decimal('35.00'),
            discount=Decimal('5.00'),
            line_total=Decimal('65.00')
        )
        self.assertEqual(sale_item.discount, Decimal('5.00'))
        self.assertEqual(sale_item.line_total, Decimal('65.00'))


class SaleSerializerTest(TestCase):
    """Test cases for Sale serializers"""
    
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
        self.sale = Sale.objects.create(
            sale_number='SALE-001',
            customer_name='Test Customer',
            payment_method='CASH',
            subtotal=Decimal('70.00'),
            total_amount=Decimal('70.00'),
            cashier=self.user
        )
        SaleItem.objects.create(
            sale=self.sale,
            product=self.product,
            quantity=2,
            unit_price=Decimal('35.00'),
            line_total=Decimal('70.00')
        )
    
    def test_sale_serializer_contains_expected_fields(self):
        """Test SaleSerializer contains all expected fields"""
        serializer = SaleSerializer(self.sale)
        expected_fields = [
            'id', 'sale_number', 'customer_name', 'payment_method',
            'subtotal', 'discount', 'total_amount', 'notes',
            'cashier', 'cashier_username', 'items', 'created_at'
        ]
        for field in expected_fields:
            self.assertIn(field, serializer.data)
    
    def test_sale_serializer_cashier_username(self):
        """Test SaleSerializer includes cashier username"""
        serializer = SaleSerializer(self.sale)
        self.assertEqual(serializer.data['cashier_username'], 'cashier')
    
    def test_sale_serializer_includes_items(self):
        """Test SaleSerializer includes sale items"""
        serializer = SaleSerializer(self.sale)
        self.assertEqual(len(serializer.data['items']), 1)
        self.assertEqual(serializer.data['items'][0]['product_name'], 'Engine Oil')


class SaleCreateSerializerTest(TestCase):
    """Test cases for SaleCreateSerializer"""
    
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
            barcode='1234567890'
        )
    
    def test_create_sale_auto_generates_sale_number(self):
        """Test sale_number is auto-generated when not provided"""
        data = {
            'payment_method': 'CASH',
            'items': [
                {'product': self.product.id, 'quantity': 2, 'unit_price': '35.00'}
            ]
        }
        
        from rest_framework.test import APIRequestFactory
        
        factory = APIRequestFactory()
        request = factory.post('/sales/')
        request.user = self.user
        
        serializer = SaleCreateSerializer(data=data, context={'request': request})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        sale = serializer.save()
        
        self.assertTrue(sale.sale_number.startswith('SALE-'))
    
    def test_create_sale_validates_empty_items(self):
        """Test validation fails when items list is empty"""
        data = {
            'payment_method': 'CASH',
            'items': []
        }
        
        from rest_framework.test import APIRequestFactory
        
        factory = APIRequestFactory()
        request = factory.post('/sales/')
        request.user = self.user
        
        serializer = SaleCreateSerializer(data=data, context={'request': request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('items', serializer.errors)
    
    def test_create_sale_updates_stock(self):
        """Test creating a sale decreases product stock"""
        initial_stock = self.product.current_stock
        
        data = {
            'payment_method': 'CASH',
            'items': [
                {'product': self.product.id, 'quantity': 5, 'unit_price': '35.00'}
            ]
        }
        
        from rest_framework.test import APIRequestFactory
        
        factory = APIRequestFactory()
        request = factory.post('/sales/')
        request.user = self.user
        
        serializer = SaleCreateSerializer(data=data, context={'request': request})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, initial_stock - 5)
    
    def test_create_sale_creates_stock_transaction(self):
        """Test creating a sale creates OUT stock transaction"""
        data = {
            'payment_method': 'CASH',
            'items': [
                {'product': self.product.id, 'quantity': 3, 'unit_price': '35.00'}
            ]
        }
        
        from rest_framework.test import APIRequestFactory
        
        factory = APIRequestFactory()
        request = factory.post('/sales/')
        request.user = self.user
        
        serializer = SaleCreateSerializer(data=data, context={'request': request})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        sale = serializer.save()
        
        transaction = StockTransaction.objects.filter(
            product=self.product,
            transaction_type='OUT',
            reason='SALE',
            reference_number=sale.sale_number
        ).first()
        
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.quantity, 3)
    
    def test_create_sale_insufficient_stock(self):
        """Test sale fails when stock is insufficient"""
        self.product.current_stock = 2
        self.product.save()
        
        data = {
            'payment_method': 'CASH',
            'items': [
                {'product': self.product.id, 'quantity': 10, 'unit_price': '35.00'}
            ]
        }
        
        from rest_framework.test import APIRequestFactory
        
        factory = APIRequestFactory()
        request = factory.post('/sales/')
        request.user = self.user
        
        serializer = SaleCreateSerializer(data=data, context={'request': request})
        self.assertTrue(serializer.is_valid())
        
        with self.assertRaises(Exception):
            serializer.save()
    
    def test_create_sale_with_barcode_lookup(self):
        """Test creating sale using barcode instead of product ID"""
        data = {
            'payment_method': 'CASH',
            'items': [
                {'barcode': '1234567890', 'quantity': 1, 'unit_price': '35.00', 'product': self.product.id}
            ]
        }
        
        from rest_framework.test import APIRequestFactory
        
        factory = APIRequestFactory()
        request = factory.post('/sales/')
        request.user = self.user
        
        serializer = SaleCreateSerializer(data=data, context={'request': request})
        self.assertTrue(serializer.is_valid(), serializer.errors)


class SaleAPITest(APITestCase):
    """Test cases for Sales API endpoints"""
    
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='admin',
            password='adminpass123',
            email='admin@test.com',
            role=User.Role.ADMIN
        )
        self.cashier_user = User.objects.create_user(
            username='cashier',
            password='cashierpass123',
            email='cashier@test.com',
            role=User.Role.CASHIER
        )
        self.viewer_user = User.objects.create_user(
            username='viewer',
            password='viewerpass123',
            email='viewer@test.com',
            role=User.Role.VIEWER
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
        self.client = APIClient()
    
    def test_create_sale_as_cashier(self):
        """Test cashier can create a sale"""
        self.client.force_authenticate(user=self.cashier_user)
        
        data = {
            'payment_method': 'CASH',
            'items': [
                {'product': self.product.id, 'quantity': 2, 'unit_price': '35.00'}
            ]
        }
        
        response = self.client.post('/api/sales/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('sale_number', response.data)
    
    def test_create_sale_as_viewer_fails(self):
        """Test viewer cannot create a sale"""
        self.client.force_authenticate(user=self.viewer_user)
        
        data = {
            'payment_method': 'CASH',
            'items': [
                {'product': self.product.id, 'quantity': 1, 'unit_price': '35.00'}
            ]
        }
        
        response = self.client.post('/api/sales/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_list_sales(self):
        """Test listing sales"""
        Sale.objects.create(
            sale_number='SALE-001',
            payment_method='CASH',
            subtotal=Decimal('70.00'),
            total_amount=Decimal('70.00'),
            cashier=self.cashier_user
        )
        
        self.client.force_authenticate(user=self.cashier_user)
        response = self.client.get('/api/sales/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_get_sale_detail(self):
        """Test retrieving sale detail"""
        sale = Sale.objects.create(
            sale_number='SALE-002',
            payment_method='CASH',
            subtotal=Decimal('50.00'),
            total_amount=Decimal('50.00'),
            cashier=self.cashier_user
        )
        
        self.client.force_authenticate(user=self.cashier_user)
        response = self.client.get(f'/api/sales/{sale.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['sale_number'], 'SALE-002')
    
    def test_filter_sales_by_payment_method(self):
        """Test filtering sales by payment method"""
        Sale.objects.create(
            sale_number='SALE-CASH',
            payment_method='CASH',
            subtotal=Decimal('50.00'),
            total_amount=Decimal('50.00'),
            cashier=self.cashier_user
        )
        Sale.objects.create(
            sale_number='SALE-CARD',
            payment_method='CARD',
            subtotal=Decimal('75.00'),
            total_amount=Decimal('75.00'),
            cashier=self.cashier_user
        )
        
        self.client.force_authenticate(user=self.cashier_user)
        response = self.client.get('/api/sales/?payment_method=CASH')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_unauthenticated_access_denied(self):
        """Test unauthenticated users cannot access sales"""
        response = self.client.get('/api/sales/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class SalesSummaryAPITest(APITestCase):
    """Test cases for sales summary endpoint"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='cashier',
            password='testpass123',
            email='cashier@test.com',
            role=User.Role.CASHIER
        )
        self.client = APIClient()
    
    def test_sales_summary_today(self):
        """Test sales summary for today"""
        Sale.objects.create(
            sale_number='SALE-001',
            payment_method='CASH',
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00'),
            cashier=self.user
        )
        Sale.objects.create(
            sale_number='SALE-002',
            payment_method='CARD',
            subtotal=Decimal('150.00'),
            total_amount=Decimal('150.00'),
            cashier=self.user
        )
        
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/sales/summary/?period=today')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_sales_count', response.data)
        self.assertIn('total_revenue', response.data)
    
    def test_sales_summary_week(self):
        """Test sales summary for week period"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/sales/summary/?period=week')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['period'], 'week')


class TopSellingProductsAPITest(APITestCase):
    """Test cases for top selling products endpoint"""
    
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
        self.client = APIClient()
    
    def test_top_selling_products(self):
        """Test top selling products endpoint"""
        sale = Sale.objects.create(
            sale_number='SALE-001',
            payment_method='CASH',
            subtotal=Decimal('70.00'),
            total_amount=Decimal('70.00'),
            cashier=self.user
        )
        SaleItem.objects.create(
            sale=sale,
            product=self.product,
            quantity=5,
            unit_price=Decimal('35.00'),
            line_total=Decimal('175.00')
        )
        
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/sales/top-products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
