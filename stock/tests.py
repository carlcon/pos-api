"""
Comprehensive Unit Tests for Stock Module
Tests for: StockTransaction model, StockAdjustmentSerializer, stock_adjustment view
"""
from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from users.models import User
from inventory.models import Category, Product
from stock.models import StockTransaction
from stock.serializers import StockTransactionSerializer, StockAdjustmentSerializer


class StockTransactionModelTest(TestCase):
    """Test cases for StockTransaction model"""
    
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
    
    def test_stock_in_transaction(self):
        """Test stock IN transaction creation"""
        transaction = StockTransaction.objects.create(
            product=self.product,
            transaction_type='IN',
            reason='PURCHASE',
            quantity=50,
            quantity_before=100,
            quantity_after=150,
            reference_number='PO-001',
            performed_by=self.user
        )
        
        self.assertEqual(transaction.transaction_type, 'IN')
        self.assertEqual(transaction.reason, 'PURCHASE')
        self.assertEqual(transaction.quantity, 50)
        self.assertEqual(transaction.quantity_before, 100)
        self.assertEqual(transaction.quantity_after, 150)
    
    def test_stock_out_transaction(self):
        """Test stock OUT transaction creation"""
        transaction = StockTransaction.objects.create(
            product=self.product,
            transaction_type='OUT',
            reason='SALE',
            quantity=10,
            quantity_before=100,
            quantity_after=90,
            reference_number='SALE-001',
            performed_by=self.user
        )
        
        self.assertEqual(transaction.transaction_type, 'OUT')
        self.assertEqual(transaction.reason, 'SALE')
        self.assertEqual(transaction.quantity_after, 90)
    
    def test_stock_adjustment_transaction(self):
        """Test stock ADJUSTMENT transaction creation"""
        transaction = StockTransaction.objects.create(
            product=self.product,
            transaction_type='ADJUSTMENT',
            reason='RECONCILIATION',
            quantity=95,
            quantity_before=100,
            quantity_after=95,
            notes='Inventory count adjustment',
            performed_by=self.user
        )
        
        self.assertEqual(transaction.transaction_type, 'ADJUSTMENT')
        self.assertEqual(transaction.reason, 'RECONCILIATION')
    
    def test_stock_transaction_str_representation(self):
        """Test stock transaction string representation"""
        transaction = StockTransaction.objects.create(
            product=self.product,
            transaction_type='IN',
            reason='PURCHASE',
            quantity=25,
            quantity_before=100,
            quantity_after=125,
            performed_by=self.user
        )
        
        str_repr = str(transaction)
        self.assertIn(self.product.name, str_repr)
    
    def test_all_transaction_type_choices(self):
        """Test all transaction type choices are valid"""
        transaction_types = ['IN', 'OUT', 'ADJUSTMENT']
        for t_type in transaction_types:
            transaction = StockTransaction.objects.create(
                product=self.product,
                transaction_type=t_type,
                reason='MANUAL',
                quantity=10,
                quantity_before=100,
                quantity_after=100,
                performed_by=self.user
            )
            self.assertEqual(transaction.transaction_type, t_type)
    
    def test_all_reason_choices(self):
        """Test all reason choices are valid"""
        reasons = ['PURCHASE', 'SALE', 'DAMAGED', 'LOST', 'RECONCILIATION', 'RETURN', 'MANUAL']
        for reason in reasons:
            transaction = StockTransaction.objects.create(
                product=self.product,
                transaction_type='ADJUSTMENT',
                reason=reason,
                quantity=5,
                quantity_before=100,
                quantity_after=100,
                performed_by=self.user
            )
            self.assertEqual(transaction.reason, reason)
    
    def test_transaction_with_notes(self):
        """Test transaction with notes"""
        notes = 'Damaged during shipping - items returned'
        transaction = StockTransaction.objects.create(
            product=self.product,
            transaction_type='OUT',
            reason='DAMAGED',
            quantity=3,
            quantity_before=100,
            quantity_after=97,
            notes=notes,
            performed_by=self.user
        )
        
        self.assertEqual(transaction.notes, notes)


class StockAdjustmentSerializerTest(TestCase):
    """Test cases for StockAdjustmentSerializer"""
    
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
            current_stock=100,
            barcode='1234567890'
        )
    
    def test_valid_in_adjustment(self):
        """Test valid IN adjustment serializer"""
        data = {
            'product_id': self.product.id,
            'adjustment_type': 'IN',
            'quantity': 50,
            'reason': 'PURCHASE',
            'reference_number': 'PO-001'
        }
        serializer = StockAdjustmentSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
    
    def test_valid_out_adjustment(self):
        """Test valid OUT adjustment serializer"""
        data = {
            'product_id': self.product.id,
            'adjustment_type': 'OUT',
            'quantity': 10,
            'reason': 'DAMAGED'
        }
        serializer = StockAdjustmentSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
    
    def test_valid_adjustment_type(self):
        """Test valid ADJUSTMENT type serializer"""
        data = {
            'product_id': self.product.id,
            'adjustment_type': 'ADJUSTMENT',
            'quantity': 95,
            'reason': 'RECONCILIATION',
            'notes': 'Physical count adjustment'
        }
        serializer = StockAdjustmentSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
    
    def test_invalid_adjustment_type(self):
        """Test invalid adjustment type fails validation"""
        data = {
            'product_id': self.product.id,
            'adjustment_type': 'INVALID',
            'quantity': 10,
            'reason': 'PURCHASE'
        }
        serializer = StockAdjustmentSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('adjustment_type', serializer.errors)
    
    def test_invalid_reason(self):
        """Test invalid reason fails validation"""
        data = {
            'product_id': self.product.id,
            'adjustment_type': 'IN',
            'quantity': 10,
            'reason': 'INVALID_REASON'
        }
        serializer = StockAdjustmentSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('reason', serializer.errors)
    
    def test_zero_quantity_fails(self):
        """Test zero quantity fails validation"""
        data = {
            'product_id': self.product.id,
            'adjustment_type': 'IN',
            'quantity': 0,
            'reason': 'PURCHASE'
        }
        serializer = StockAdjustmentSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('quantity', serializer.errors)
    
    def test_negative_quantity_fails(self):
        """Test negative quantity fails validation"""
        data = {
            'product_id': self.product.id,
            'adjustment_type': 'IN',
            'quantity': -5,
            'reason': 'PURCHASE'
        }
        serializer = StockAdjustmentSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('quantity', serializer.errors)
    
    def test_optional_barcode(self):
        """Test barcode field is optional"""
        data = {
            'product_id': self.product.id,
            'barcode': '',
            'adjustment_type': 'IN',
            'quantity': 10,
            'reason': 'PURCHASE'
        }
        serializer = StockAdjustmentSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)


class StockTransactionSerializerTest(TestCase):
    """Test cases for StockTransactionSerializer"""
    
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
        self.transaction = StockTransaction.objects.create(
            product=self.product,
            transaction_type='IN',
            reason='PURCHASE',
            quantity=50,
            quantity_before=100,
            quantity_after=150,
            reference_number='PO-001',
            performed_by=self.user
        )
    
    def test_serializer_contains_expected_fields(self):
        """Test serializer contains all expected fields"""
        serializer = StockTransactionSerializer(self.transaction)
        expected_fields = [
            'id', 'product', 'product_name', 'product_sku',
            'transaction_type', 'transaction_type_display',
            'reason', 'reason_display', 'quantity',
            'quantity_before', 'quantity_after', 'reference_number',
            'notes', 'performed_by', 'performed_by_username', 'created_at'
        ]
        for field in expected_fields:
            self.assertIn(field, serializer.data)
    
    def test_serializer_product_name(self):
        """Test serializer includes product name"""
        serializer = StockTransactionSerializer(self.transaction)
        self.assertEqual(serializer.data['product_name'], 'Engine Oil')
    
    def test_serializer_performed_by_username(self):
        """Test serializer includes username of performer"""
        serializer = StockTransactionSerializer(self.transaction)
        self.assertEqual(serializer.data['performed_by_username'], 'inventory_staff')


class StockAdjustmentAPITest(APITestCase):
    """Test cases for stock adjustment API endpoint"""
    
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='admin',
            password='adminpass123',
            email='admin@test.com',
            role=User.Role.ADMIN
        )
        self.inventory_staff = User.objects.create_user(
            username='inventory_staff',
            password='staffpass123',
            email='staff@test.com',
            role=User.Role.INVENTORY_STAFF
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
            current_stock=100,
            barcode='1234567890'
        )
        self.client = APIClient()
    
    def test_stock_in_adjustment_by_inventory_staff(self):
        """Test inventory staff can add stock"""
        self.client.force_authenticate(user=self.inventory_staff)
        
        data = {
            'product_id': self.product.id,
            'adjustment_type': 'IN',
            'quantity': 50,
            'reason': 'PURCHASE',
            'reference_number': 'PO-001'
        }
        
        response = self.client.post('/api/stock/adjust/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify stock was updated
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, 150)
    
    def test_stock_out_adjustment_by_admin(self):
        """Test admin can remove stock"""
        self.client.force_authenticate(user=self.admin_user)
        
        data = {
            'product_id': self.product.id,
            'adjustment_type': 'OUT',
            'quantity': 10,
            'reason': 'DAMAGED',
            'notes': 'Items damaged in warehouse'
        }
        
        response = self.client.post('/api/stock/adjust/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify stock was updated
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, 90)
    
    def test_stock_adjustment_set_quantity(self):
        """Test ADJUSTMENT sets exact quantity"""
        self.client.force_authenticate(user=self.inventory_staff)
        
        data = {
            'product_id': self.product.id,
            'adjustment_type': 'ADJUSTMENT',
            'quantity': 75,
            'reason': 'RECONCILIATION',
            'notes': 'Physical count revealed 75 units'
        }
        
        response = self.client.post('/api/stock/adjust/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify stock was set to exact quantity
        self.product.refresh_from_db()
        self.assertEqual(self.product.current_stock, 75)
    
    def test_cashier_cannot_adjust_stock(self):
        """Test cashier cannot adjust stock"""
        self.client.force_authenticate(user=self.cashier_user)
        
        data = {
            'product_id': self.product.id,
            'adjustment_type': 'IN',
            'quantity': 10,
            'reason': 'PURCHASE'
        }
        
        response = self.client.post('/api/stock/adjust/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_viewer_cannot_adjust_stock(self):
        """Test viewer cannot adjust stock"""
        self.client.force_authenticate(user=self.viewer_user)
        
        data = {
            'product_id': self.product.id,
            'adjustment_type': 'IN',
            'quantity': 10,
            'reason': 'PURCHASE'
        }
        
        response = self.client.post('/api/stock/adjust/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_stock_out_insufficient_quantity(self):
        """Test OUT fails when insufficient stock"""
        self.client.force_authenticate(user=self.inventory_staff)
        
        data = {
            'product_id': self.product.id,
            'adjustment_type': 'OUT',
            'quantity': 150,  # More than available
            'reason': 'DAMAGED'
        }
        
        response = self.client.post('/api/stock/adjust/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_adjustment_creates_transaction_record(self):
        """Test adjustment creates stock transaction record"""
        self.client.force_authenticate(user=self.inventory_staff)
        
        initial_count = StockTransaction.objects.count()
        
        data = {
            'product_id': self.product.id,
            'adjustment_type': 'IN',
            'quantity': 25,
            'reason': 'RETURN',
            'reference_number': 'RET-001'
        }
        
        response = self.client.post('/api/stock/adjust/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify transaction was created
        self.assertEqual(StockTransaction.objects.count(), initial_count + 1)
        
        transaction = StockTransaction.objects.latest('created_at')
        self.assertEqual(transaction.product, self.product)
        self.assertEqual(transaction.transaction_type, 'IN')
        self.assertEqual(transaction.quantity, 25)
    
    def test_adjustment_by_barcode(self):
        """Test adjustment using barcode lookup"""
        self.client.force_authenticate(user=self.inventory_staff)
        
        data = {
            'product_id': self.product.id,
            'barcode': '1234567890',
            'adjustment_type': 'IN',
            'quantity': 20,
            'reason': 'PURCHASE'
        }
        
        response = self.client.post('/api/stock/adjust/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_unauthenticated_adjustment_denied(self):
        """Test unauthenticated users cannot adjust stock"""
        data = {
            'product_id': self.product.id,
            'adjustment_type': 'IN',
            'quantity': 10,
            'reason': 'PURCHASE'
        }
        
        response = self.client.post('/api/stock/adjust/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class StockTransactionListAPITest(APITestCase):
    """Test cases for stock transaction list API"""
    
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
        StockTransaction.objects.create(
            product=self.product,
            transaction_type='IN',
            reason='PURCHASE',
            quantity=50,
            quantity_before=50,
            quantity_after=100,
            performed_by=self.user
        )
        self.client = APIClient()
    
    def test_list_transactions(self):
        """Test listing stock transactions"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/stock/transactions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_filter_by_product(self):
        """Test filtering transactions by product"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/stock/transactions/?product={self.product.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_filter_by_transaction_type(self):
        """Test filtering transactions by type"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/stock/transactions/?type=IN')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class LowStockAPITest(APITestCase):
    """Test cases for low stock products API"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='cashier',
            password='testpass123',
            email='cashier@test.com',
            role=User.Role.CASHIER
        )
        self.category = Category.objects.create(name='Engine Parts')
        # Low stock product
        self.low_stock_product = Product.objects.create(
            sku='ENG-001',
            name='Engine Oil',
            category=self.category,
            cost_price=Decimal('25.00'),
            selling_price=Decimal('35.00'),
            current_stock=5,
            minimum_stock_level=10,
            is_active=True
        )
        # Adequate stock product
        self.adequate_stock_product = Product.objects.create(
            sku='ENG-002',
            name='Brake Fluid',
            category=self.category,
            cost_price=Decimal('15.00'),
            selling_price=Decimal('25.00'),
            current_stock=100,
            minimum_stock_level=10,
            is_active=True
        )
        self.client = APIClient()
    
    def test_low_stock_products(self):
        """Test low stock products endpoint"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/stock/low-stock/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('count', response.data)
        self.assertIn('products', response.data)
        
        # Should include low stock product
        product_ids = [p['id'] for p in response.data['products']]
        self.assertIn(self.low_stock_product.id, product_ids)
        
        # Should NOT include adequate stock product
        self.assertNotIn(self.adequate_stock_product.id, product_ids)
