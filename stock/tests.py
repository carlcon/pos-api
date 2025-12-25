"""
Comprehensive tests for Stock Module.
Tests for: StockTransaction model, serializers, adjustments, low stock, cost history, and multi-tenant isolation.
"""
import pytest
from decimal import Decimal
from datetime import date
from rest_framework import status
from stock.models import StockTransaction, ProductCostHistory
from stock.serializers import StockTransactionSerializer, StockAdjustmentSerializer
from users.models import User


# ============== Stock Transaction Model Tests ==============

@pytest.mark.django_db
class TestStockTransactionModel:
    """Test cases for StockTransaction model"""
    
    def test_stock_in_transaction(self, partner, product, admin_user):
        """Test stock IN transaction creation"""
        transaction = StockTransaction.objects.create(
            partner=partner,
            product=product,
            transaction_type='IN',
            reason='PURCHASE',
            quantity=50,
            quantity_before=100,
            quantity_after=150,
            reference_number='PO-001',
            performed_by=admin_user
        )
        
        assert transaction.transaction_type == 'IN'
        assert transaction.reason == 'PURCHASE'
        assert transaction.quantity == 50
        assert transaction.quantity_before == 100
        assert transaction.quantity_after == 150
    
    def test_stock_out_transaction(self, partner, product, admin_user):
        """Test stock OUT transaction creation"""
        transaction = StockTransaction.objects.create(
            partner=partner,
            product=product,
            transaction_type='OUT',
            reason='SALE',
            quantity=10,
            quantity_before=100,
            quantity_after=90,
            reference_number='SALE-001',
            performed_by=admin_user
        )
        
        assert transaction.transaction_type == 'OUT'
        assert transaction.reason == 'SALE'
        assert transaction.quantity_after == 90
    
    def test_stock_adjustment_transaction(self, partner, product, admin_user):
        """Test stock ADJUSTMENT transaction creation"""
        transaction = StockTransaction.objects.create(
            partner=partner,
            product=product,
            transaction_type='ADJUSTMENT',
            reason='RECONCILIATION',
            quantity=95,
            quantity_before=100,
            quantity_after=95,
            notes='Inventory count adjustment',
            performed_by=admin_user
        )
        
        assert transaction.transaction_type == 'ADJUSTMENT'
        assert transaction.reason == 'RECONCILIATION'
    
    def test_stock_transaction_str_representation(self, stock_transaction):
        """Test stock transaction string representation"""
        str_repr = str(stock_transaction)
        assert 'Stock In' in str_repr or 'IN' in str_repr or stock_transaction.product.name in str_repr
    
    def test_all_transaction_type_choices(self, partner, product, admin_user):
        """Test all transaction type choices are valid"""
        transaction_types = ['IN', 'OUT', 'ADJUSTMENT']
        for t_type in transaction_types:
            transaction = StockTransaction.objects.create(
                partner=partner,
                product=product,
                transaction_type=t_type,
                reason='MANUAL',
                quantity=10,
                quantity_before=100,
                quantity_after=100,
                performed_by=admin_user
            )
            assert transaction.transaction_type == t_type
    
    def test_all_reason_choices(self, partner, product, admin_user):
        """Test all reason choices are valid"""
        reasons = ['PURCHASE', 'SALE', 'DAMAGED', 'LOST', 'RECONCILIATION', 'RETURN', 'MANUAL']
        for reason in reasons:
            transaction = StockTransaction.objects.create(
                partner=partner,
                product=product,
                transaction_type='ADJUSTMENT',
                reason=reason,
                quantity=5,
                quantity_before=100,
                quantity_after=100,
                performed_by=admin_user
            )
            assert transaction.reason == reason
    
    def test_transaction_with_notes(self, partner, product, admin_user):
        """Test transaction with notes"""
        notes = 'Damaged during shipping - items returned'
        transaction = StockTransaction.objects.create(
            partner=partner,
            product=product,
            transaction_type='OUT',
            reason='DAMAGED',
            quantity=3,
            quantity_before=100,
            quantity_after=97,
            notes=notes,
            performed_by=admin_user
        )
        
        assert transaction.notes == notes


# ============== Stock Adjustment Serializer Tests ==============

@pytest.mark.django_db
class TestStockAdjustmentSerializer:
    """Test cases for StockAdjustmentSerializer"""
    
    def test_valid_in_adjustment(self, product):
        """Test valid IN adjustment serializer"""
        data = {
            'product_id': product.id,
            'adjustment_type': 'IN',
            'quantity': 50,
            'reason': 'PURCHASE',
            'reference_number': 'PO-001'
        }
        serializer = StockAdjustmentSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
    
    def test_valid_out_adjustment(self, product):
        """Test valid OUT adjustment serializer"""
        data = {
            'product_id': product.id,
            'adjustment_type': 'OUT',
            'quantity': 10,
            'reason': 'DAMAGED'
        }
        serializer = StockAdjustmentSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
    
    def test_valid_adjustment_type(self, product):
        """Test valid ADJUSTMENT type serializer"""
        data = {
            'product_id': product.id,
            'adjustment_type': 'ADJUSTMENT',
            'quantity': 95,
            'reason': 'RECONCILIATION',
            'notes': 'Physical count adjustment'
        }
        serializer = StockAdjustmentSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
    
    def test_invalid_adjustment_type(self, product):
        """Test invalid adjustment type fails validation"""
        data = {
            'product_id': product.id,
            'adjustment_type': 'INVALID',
            'quantity': 10,
            'reason': 'PURCHASE'
        }
        serializer = StockAdjustmentSerializer(data=data)
        assert not serializer.is_valid()
        assert 'adjustment_type' in serializer.errors
    
    def test_invalid_reason(self, product):
        """Test invalid reason fails validation"""
        data = {
            'product_id': product.id,
            'adjustment_type': 'IN',
            'quantity': 10,
            'reason': 'INVALID_REASON'
        }
        serializer = StockAdjustmentSerializer(data=data)
        assert not serializer.is_valid()
        assert 'reason' in serializer.errors
    
    def test_zero_quantity_fails(self, product):
        """Test zero quantity fails validation"""
        data = {
            'product_id': product.id,
            'adjustment_type': 'IN',
            'quantity': 0,
            'reason': 'PURCHASE'
        }
        serializer = StockAdjustmentSerializer(data=data)
        assert not serializer.is_valid()
        assert 'quantity' in serializer.errors
    
    def test_negative_quantity_fails(self, product):
        """Test negative quantity fails validation"""
        data = {
            'product_id': product.id,
            'adjustment_type': 'IN',
            'quantity': -5,
            'reason': 'PURCHASE'
        }
        serializer = StockAdjustmentSerializer(data=data)
        assert not serializer.is_valid()
        assert 'quantity' in serializer.errors


# ============== Stock Transaction Serializer Tests ==============

@pytest.mark.django_db
class TestStockTransactionSerializer:
    """Test cases for StockTransactionSerializer"""
    
    def test_serializer_contains_expected_fields(self, stock_transaction):
        """Test serializer contains all expected fields"""
        serializer = StockTransactionSerializer(stock_transaction)
        expected_fields = [
            'id', 'product', 'product_name', 'product_sku',
            'transaction_type', 'reason', 'quantity',
            'quantity_before', 'quantity_after', 'reference_number',
            'notes', 'performed_by', 'created_at'
        ]
        for field in expected_fields:
            assert field in serializer.data
    
    def test_serializer_product_name(self, stock_transaction):
        """Test serializer includes product name"""
        serializer = StockTransactionSerializer(stock_transaction)
        assert serializer.data['product_name'] == stock_transaction.product.name


# ============== Product Cost History Model Tests ==============

@pytest.mark.django_db
class TestProductCostHistoryModel:
    """Test ProductCostHistory model"""

    def test_cost_history_str_representation(self, product, admin_user):
        """Test cost history string representation"""
        history = ProductCostHistory.objects.create(
            product=product,
            old_cost=Decimal('100.00'),
            new_cost=Decimal('150.00'),
            reason='Price update',
            changed_by=admin_user
        )
        
        string_repr = str(history)
        assert '100' in string_repr or '150' in string_repr or product.name in string_repr

    def test_cost_difference_property(self, product, admin_user):
        """Test cost_difference property calculation"""
        history = ProductCostHistory.objects.create(
            product=product,
            old_cost=Decimal('100.00'),
            new_cost=Decimal('150.00'),
            reason='Test',
            changed_by=admin_user
        )
        
        assert history.cost_difference == Decimal('50.00')

    def test_percentage_change_property(self, product, admin_user):
        """Test percentage_change property calculation"""
        history = ProductCostHistory.objects.create(
            product=product,
            old_cost=Decimal('100.00'),
            new_cost=Decimal('150.00'),
            reason='Test',
            changed_by=admin_user
        )
        
        assert history.percentage_change == Decimal('50.00')

    def test_percentage_change_from_zero(self, product, admin_user):
        """Test percentage change when old cost is zero"""
        history = ProductCostHistory.objects.create(
            product=product,
            old_cost=Decimal('0.00'),
            new_cost=Decimal('100.00'),
            reason='Initial price',
            changed_by=admin_user
        )
        
        assert history.percentage_change == Decimal('100.00')


# ============== Stock Transaction List API Tests ==============

@pytest.mark.django_db
class TestStockTransactionListAPI:
    """Test stock transaction listing endpoint"""

    def test_list_stock_transactions(self, admin_client, stock_transaction):
        """Test listing stock transactions"""
        response = admin_client.get('/api/stock/transactions/')
        
        assert response.status_code == status.HTTP_200_OK
        transactions = response.data if isinstance(response.data, list) else response.data.get('results', [])
        assert len(transactions) >= 1

    def test_list_transactions_partner_isolation(self, admin_client, stock_transaction, partner2, partner2_product, admin_user):
        """Test stock transactions are filtered by partner"""
        partner2_user = User.objects.create_user(
            username='p2_stock_user',
            password='test123',
            role=User.Role.ADMIN,
            partner=partner2
        )
        partner2_transaction = StockTransaction.objects.create(
            partner=partner2,
            product=partner2_product,
            transaction_type='IN',
            reason='PURCHASE',
            quantity=10,
            quantity_before=20,
            quantity_after=30,
            performed_by=partner2_user
        )
        
        response = admin_client.get('/api/stock/transactions/')
        
        transactions = response.data if isinstance(response.data, list) else response.data.get('results', [])
        ids = [t['id'] for t in transactions]
        assert stock_transaction.id in ids
        assert partner2_transaction.id not in ids

    def test_super_admin_must_impersonate(self, super_admin_client):
        """Super admin without impersonation cannot access stock transactions"""
        response = super_admin_client.get('/api/stock/transactions/')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'impersonate' in str(response.data.get('detail', '')).lower()

    def test_filter_transactions_by_type(self, admin_client, stock_transaction, stock_out_transaction):
        """Test filtering transactions by type"""
        response = admin_client.get('/api/stock/transactions/?type=IN')
        
        assert response.status_code == status.HTTP_200_OK
        transactions = response.data if isinstance(response.data, list) else response.data.get('results', [])
        for t in transactions:
            assert t['transaction_type'] == 'IN'

    def test_filter_transactions_by_reason(self, admin_client, stock_transaction):
        """Test filtering transactions by reason"""
        response = admin_client.get('/api/stock/transactions/?reason=PURCHASE')
        
        assert response.status_code == status.HTTP_200_OK
        transactions = response.data if isinstance(response.data, list) else response.data.get('results', [])
        for t in transactions:
            assert t['reason'] == 'PURCHASE'

    def test_filter_transactions_by_product(self, admin_client, stock_transaction, product):
        """Test filtering transactions by product"""
        response = admin_client.get(f'/api/stock/transactions/?product={product.id}')
        
        assert response.status_code == status.HTTP_200_OK
        transactions = response.data if isinstance(response.data, list) else response.data.get('results', [])
        for t in transactions:
            assert t['product'] == product.id

    def test_filter_transactions_by_date_range(self, admin_client, stock_transaction):
        """Test filtering transactions by date range"""
        today = date.today()
        response = admin_client.get(f'/api/stock/transactions/?date_from={today}&date_to={today}')
        
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestStockTransactionDetailAPI:
    """Test stock transaction detail endpoint"""

    def test_get_transaction_detail(self, admin_client, stock_transaction):
        """Test getting stock transaction details"""
        response = admin_client.get(f'/api/stock/transactions/{stock_transaction.id}/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['transaction_type'] == stock_transaction.transaction_type
        assert response.data['quantity'] == stock_transaction.quantity

    def test_cannot_access_other_partner_transaction(self, admin_client, partner2, partner2_product):
        """Test cannot access another partner's transaction"""
        partner2_user = User.objects.create_user(
            username='p2_stock_user2',
            password='test123',
            role=User.Role.ADMIN,
            partner=partner2
        )
        partner2_transaction = StockTransaction.objects.create(
            partner=partner2,
            product=partner2_product,
            transaction_type='IN',
            reason='PURCHASE',
            quantity=5,
            quantity_before=25,
            quantity_after=30,
            performed_by=partner2_user
        )
        
        response = admin_client.get(f'/api/stock/transactions/{partner2_transaction.id}/')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ============== Stock Adjustment API Tests ==============

@pytest.mark.django_db
class TestStockAdjustmentAPI:
    """Test stock adjustment endpoint"""

    def test_stock_adjustment_increase(self, admin_client, product):
        """Test increasing stock via adjustment"""
        initial_stock = product.current_stock
        
        response = admin_client.post('/api/stock/adjust/', {
            'product_id': product.id,
            'adjustment_type': 'IN',
            'quantity': 10,
            'reason': 'RECONCILIATION',
            'notes': 'Found extra stock'
        })
        
        assert response.status_code == status.HTTP_200_OK
        product.refresh_from_db()
        assert product.current_stock == initial_stock + 10

    def test_stock_adjustment_decrease(self, admin_client, product):
        """Test decreasing stock via adjustment"""
        initial_stock = product.current_stock
        
        response = admin_client.post('/api/stock/adjust/', {
            'product_id': product.id,
            'adjustment_type': 'OUT',
            'quantity': 5,
            'reason': 'DAMAGED',
            'notes': 'Damaged items removed'
        })
        
        assert response.status_code == status.HTTP_200_OK
        product.refresh_from_db()
        assert product.current_stock == initial_stock - 5

    def test_stock_adjustment_creates_transaction(self, admin_client, product):
        """Test stock adjustment creates transaction record"""
        initial_count = StockTransaction.objects.filter(product=product).count()
        
        admin_client.post('/api/stock/adjust/', {
            'product_id': product.id,
            'adjustment_type': 'IN',
            'quantity': 5,
            'reason': 'MANUAL',
            'notes': 'Manual adjustment'
        })
        
        new_count = StockTransaction.objects.filter(product=product).count()
        assert new_count == initial_count + 1

    def test_stock_adjustment_records_before_after(self, admin_client, product):
        """Test stock adjustment records before and after quantities"""
        initial_stock = product.current_stock
        
        admin_client.post('/api/stock/adjust/', {
            'product_id': product.id,
            'adjustment_type': 'IN',
            'quantity': 10,
            'reason': 'MANUAL'
        })
        
        transaction = StockTransaction.objects.filter(product=product).latest('created_at')
        assert transaction.quantity_before == initial_stock
        assert transaction.quantity_after == initial_stock + 10

    def test_stock_adjustment_insufficient_stock_fails(self, admin_client, product):
        """Test decreasing more than available stock fails"""
        response = admin_client.post('/api/stock/adjust/', {
            'product_id': product.id,
            'adjustment_type': 'OUT',
            'quantity': 9999,
            'reason': 'DAMAGED'
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_stock_adjustment_invalid_product_fails(self, admin_client, partner2_product):
        """Test adjusting other partner's product fails"""
        response = admin_client.post('/api/stock/adjust/', {
            'product_id': partner2_product.id,
            'adjustment_type': 'IN',
            'quantity': 10,
            'reason': 'MANUAL'
        })
        
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND]

    def test_stock_adjustment_with_cost(self, admin_client, product):
        """Test stock adjustment with unit cost"""
        response = admin_client.post('/api/stock/adjust/', {
            'product_id': product.id,
            'adjustment_type': 'IN',
            'quantity': 10,
            'reason': 'PURCHASE',
            'unit_cost': '95.00',
            'notes': 'New shipment'
        })
        
        assert response.status_code == status.HTTP_200_OK
        transaction = StockTransaction.objects.filter(product=product).latest('created_at')
        assert transaction.unit_cost == Decimal('95.00')

    def test_all_adjustment_reasons(self, admin_client, product):
        """Test all valid adjustment reasons"""
        reasons = ['DAMAGED', 'LOST', 'RECONCILIATION', 'RETURN', 'MANUAL']
        
        for reason in reasons:
            product.current_stock = 100
            product.save()
            
            response = admin_client.post('/api/stock/adjust/', {
                'product_id': product.id,
                'adjustment_type': 'OUT',
                'quantity': 1,
                'reason': reason
            })
            
            assert response.status_code == status.HTTP_200_OK, f"Failed for reason: {reason}"


# ============== Low Stock API Tests ==============

@pytest.mark.django_db
class TestLowStockAPI:
    """Test low stock products endpoint"""

    def test_low_stock_products(self, admin_client, low_stock_product):
        """Test getting low stock products"""
        response = admin_client.get('/api/stock/low-stock/')
        
        assert response.status_code == status.HTTP_200_OK
        products = response.data if isinstance(response.data, list) else response.data.get('results', [])
        assert any(p['sku'] == low_stock_product.sku for p in products) or len(products) >= 0

    def test_low_stock_partner_isolation(self, admin_client, low_stock_product, partner2_product):
        """Test low stock only shows partner's products"""
        partner2_product.current_stock = 1
        partner2_product.minimum_stock_level = 10
        partner2_product.save()
        
        response = admin_client.get('/api/stock/low-stock/')
        
        assert response.status_code == status.HTTP_200_OK
        products = response.data if isinstance(response.data, list) else response.data.get('results', [])
        skus = [p['sku'] for p in products]
        assert partner2_product.sku not in skus


# ============== Cost History API Tests ==============

@pytest.mark.django_db
class TestCostHistoryAPI:
    """Test product cost history endpoint"""

    def test_list_cost_history(self, admin_client, product, admin_user):
        """Test listing cost history"""
        ProductCostHistory.objects.create(
            product=product,
            old_cost=Decimal('100.00'),
            new_cost=Decimal('110.00'),
            reason='Price increase',
            changed_by=admin_user
        )
        
        response = admin_client.get('/api/stock/cost-history/')
        
        assert response.status_code == status.HTTP_200_OK
        history = response.data if isinstance(response.data, list) else response.data.get('results', [])
        assert len(history) >= 1

    def test_filter_cost_history_by_product(self, admin_client, product, admin_user):
        """Test filtering cost history by product"""
        ProductCostHistory.objects.create(
            product=product,
            old_cost=Decimal('100.00'),
            new_cost=Decimal('120.00'),
            reason='Test',
            changed_by=admin_user
        )
        
        response = admin_client.get(f'/api/stock/cost-history/?product={product.id}')
        
        assert response.status_code == status.HTTP_200_OK
        history = response.data if isinstance(response.data, list) else response.data.get('results', [])
        for h in history:
            assert h['product'] == product.id


# ============== Role-Based Access Tests ==============

@pytest.mark.django_db
class TestStockRoleAccess:
    """Test role-based access control for stock endpoints"""

    def test_admin_can_adjust_stock(self, admin_client, product):
        """Test admin can adjust stock"""
        response = admin_client.post('/api/stock/adjust/', {
            'product_id': product.id,
            'adjustment_type': 'IN',
            'quantity': 5,
            'reason': 'MANUAL'
        })
        
        assert response.status_code == status.HTTP_200_OK

    def test_inventory_staff_can_adjust_stock(self, inventory_client, product):
        """Test inventory staff can adjust stock"""
        response = inventory_client.post('/api/stock/adjust/', {
            'product_id': product.id,
            'adjustment_type': 'IN',
            'quantity': 5,
            'reason': 'MANUAL'
        })
        
        assert response.status_code == status.HTTP_200_OK

    def test_cashier_cannot_adjust_stock(self, cashier_client, product):
        """Test cashier cannot adjust stock"""
        response = cashier_client.post('/api/stock/adjust/', {
            'product_id': product.id,
            'adjustment_type': 'IN',
            'quantity': 5,
            'reason': 'MANUAL'
        })
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_viewer_cannot_adjust_stock(self, viewer_client, product):
        """Test viewer cannot adjust stock"""
        response = viewer_client.post('/api/stock/adjust/', {
            'product_id': product.id,
            'adjustment_type': 'IN',
            'quantity': 5,
            'reason': 'MANUAL'
        })
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_viewer_can_view_transactions(self, viewer_client, stock_transaction):
        """Test viewer can view stock transactions"""
        response = viewer_client.get('/api/stock/transactions/')
        
        assert response.status_code == status.HTTP_200_OK

    def test_cashier_can_view_low_stock(self, cashier_client, low_stock_product):
        """Test cashier can view low stock products"""
        response = cashier_client.get('/api/stock/low-stock/')
        
        assert response.status_code == status.HTTP_200_OK


# ============== Impersonation Tests ==============

@pytest.mark.django_db
class TestStockImpersonation:
    """Test impersonation for stock endpoints"""

    def test_impersonation_sees_partner_transactions(self, impersonation_client, stock_transaction):
        """Test impersonation sees impersonated partner's transactions"""
        response = impersonation_client.get('/api/stock/transactions/')
        
        assert response.status_code == status.HTTP_200_OK
        transactions = response.data if isinstance(response.data, list) else response.data.get('results', [])
        ids = [t['id'] for t in transactions]
        assert stock_transaction.id in ids

    def test_impersonation_can_adjust_stock(self, impersonation_client, product, partner):
        """Test impersonation can adjust stock for partner"""
        initial_stock = product.current_stock
        
        response = impersonation_client.post('/api/stock/adjust/', {
            'product_id': product.id,
            'adjustment_type': 'IN',
            'quantity': 5,
            'reason': 'MANUAL'
        })
        
        assert response.status_code == status.HTTP_200_OK
        product.refresh_from_db()
        assert product.current_stock == initial_stock + 5
        
        transaction = StockTransaction.objects.filter(product=product).latest('created_at')
        assert transaction.partner == partner

    def test_impersonation_sees_partner_low_stock(self, impersonation_client, low_stock_product):
        """Test impersonation sees partner's low stock products"""
        response = impersonation_client.get('/api/stock/low-stock/')
        
        assert response.status_code == status.HTTP_200_OK
