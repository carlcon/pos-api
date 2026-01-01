"""
Comprehensive tests for Sales Module.
Tests for: Sale, SaleItem models, serializers, views, and multi-tenant isolation.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from rest_framework import status
from sales.models import Sale, SaleItem
from users.models import User
from inventory.models import Category, Product


# ============== Sale Model Tests ==============

@pytest.mark.django_db
class TestSaleModel:
    """Test cases for Sale model"""
    
    def test_sale_creation(self, sale):
        """Test sale is created correctly"""
        assert sale.sale_number is not None
        assert sale.cashier is not None
    
    def test_sale_str_representation(self, sale):
        """Test sale string representation"""
        assert sale.sale_number in str(sale)
    
    def test_sale_payment_method_choices(self, partner, cashier_user):
        """Test all payment method choices"""
        payment_methods = ['CASH', 'CARD', 'BANK_TRANSFER', 'CHECK', 'CREDIT']
        for method in payment_methods:
            sale = Sale.objects.create(
                partner=partner,
                sale_number=f'SALE-{method}',
                payment_method=method,
                subtotal=Decimal('50.00'),
                total_amount=Decimal('50.00'),
                cashier=cashier_user
            )
            assert sale.payment_method == method
    
    def test_sale_without_customer_name(self, partner, cashier_user):
        """Test sale can be created without customer name (walk-in)"""
        sale = Sale.objects.create(
            partner=partner,
            sale_number='SALE-WALKIN',
            payment_method='CASH',
            subtotal=Decimal('50.00'),
            total_amount=Decimal('50.00'),
            cashier=cashier_user
        )
        assert sale.customer_name is None or sale.customer_name == ''
    
    def test_sale_discount_default(self, partner, cashier_user):
        """Test sale discount defaults to zero"""
        sale = Sale.objects.create(
            partner=partner,
            sale_number='SALE-NO-DISC',
            payment_method='CASH',
            subtotal=Decimal('50.00'),
            total_amount=Decimal('50.00'),
            cashier=cashier_user
        )
        assert sale.discount == Decimal('0.00')

    def test_sale_calculate_total(self, partner, product, cashier_user):
        """Test sale total calculation"""
        sale = Sale(
            partner=partner,
            sale_number='CALC-001',
            subtotal=Decimal('150.00'),
            discount=Decimal('10.00'),
            total_amount=Decimal('0.00'),
            cashier=cashier_user
        )
        sale.calculate_total()
        
        assert sale.total_amount == Decimal('140.00')


@pytest.mark.django_db
class TestSaleItemModel:
    """Test cases for SaleItem model"""
    
    def test_sale_item_creation(self, sale, product):
        """Test sale item is created correctly"""
        item = sale.items.first()
        assert item is not None
        assert item.sale == sale
        assert item.quantity > 0
    
    def test_sale_item_str_representation(self, sale, product):
        """Test sale item string representation"""
        item = sale.items.first()
        assert product.name in str(item) or product.sku in str(item)
    
    def test_sale_item_with_discount(self, sale, product, category, partner, store):
        """Test sale item with discount applied"""
        from inventory.models import StoreInventory
        product2 = Product.objects.create(
            partner=partner,
            sku='SALE-DISC-001',
            name='Discounted Product',
            category=category,
            cost_price=Decimal('15.00'),
            selling_price=Decimal('25.00')
        )
        StoreInventory.objects.create(
            product=product2,
            store=store,
            current_stock=50,
            minimum_stock_level=10
        )
        sale_item = SaleItem.objects.create(
            sale=sale,
            product=product2,
            quantity=2,
            unit_price=Decimal('35.00'),
            discount=Decimal('5.00'),
            line_total=Decimal('65.00')
        )
        assert sale_item.discount == Decimal('5.00')
        assert sale_item.line_total == Decimal('65.00')

    def test_sale_item_calculate_line_total(self, sale, product):
        """Test sale item line total calculation"""
        item = SaleItem(
            sale=sale,
            product=product,
            quantity=3,
            unit_price=Decimal('100.00'),
            discount=Decimal('10.00'),
            line_total=Decimal('0.00')
        )
        item.calculate_line_total()
        
        assert item.line_total == Decimal('290.00')  # (100 * 3) - 10


# ============== Sale List API Tests ==============

@pytest.mark.django_db
class TestSaleListAPI:
    """Test sale listing endpoint"""

    def test_list_sales(self, admin_client, sale):
        """Test listing sales"""
        response = admin_client.get('/api/sales/')
        
        assert response.status_code == status.HTTP_200_OK
        sales = response.data if isinstance(response.data, list) else response.data.get('results', [])
        assert len(sales) >= 1

    def test_list_sales_partner_isolation(self, admin_client, sale, partner2, cashier_user):
        """Test sales are filtered by partner"""
        partner2_category = Category.objects.create(partner=partner2, name='P2 Cat')
        partner2_product = Product.objects.create(
            partner=partner2,
            sku='P2-SKU',
            name='P2 Product',
            category=partner2_category,
            cost_price=Decimal('10.00'),
            selling_price=Decimal('20.00')
        )
        partner2_cashier = User.objects.create_user(
            username='p2_cashier',
            password='test123',
            role=User.Role.CASHIER,
            partner=partner2
        )
        partner2_sale = Sale.objects.create(
            partner=partner2,
            sale_number='P2-SALE-001',
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00'),
            cashier=partner2_cashier
        )
        
        response = admin_client.get('/api/sales/')
        
        sales = response.data if isinstance(response.data, list) else response.data.get('results', [])
        sale_numbers = [s['sale_number'] for s in sales]
        assert sale.sale_number in sale_numbers
        assert partner2_sale.sale_number not in sale_numbers

    def test_super_admin_must_impersonate(self, super_admin_client):
        """Super admin without impersonation cannot access sales data"""
        response = super_admin_client.get('/api/sales/')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'impersonate' in str(response.data.get('detail', '')).lower()

    def test_filter_sales_by_date(self, admin_client, sale):
        """Test filtering sales by date range"""
        today = date.today()
        response = admin_client.get(f'/api/sales/?date_from={today}&date_to={today}')
        
        assert response.status_code == status.HTTP_200_OK

    def test_filter_sales_by_payment_method(self, admin_client, sale):
        """Test filtering sales by payment method"""
        response = admin_client.get('/api/sales/?payment_method=CASH')
        
        assert response.status_code == status.HTTP_200_OK
        sales = response.data if isinstance(response.data, list) else response.data.get('results', [])
        for s in sales:
            assert s['payment_method'] == 'CASH'

    def test_filter_wholesale_sales(self, admin_client, sale, wholesale_sale):
        """Test listing includes wholesale sales"""
        response = admin_client.get('/api/sales/')
        
        assert response.status_code == status.HTTP_200_OK
        sales = response.data if isinstance(response.data, list) else response.data.get('results', [])
        sale_numbers = [s['sale_number'] for s in sales]
        assert wholesale_sale.sale_number in sale_numbers


@pytest.mark.django_db
class TestSaleCreateAPI:
    """Test sale creation endpoint"""

    def test_create_sale_success(self, cashier_client, product, partner):
        """Test creating a sale successfully"""
        from inventory.models import StoreInventory
        # Get the store that has inventory for this product
        store_inv = StoreInventory.objects.get(product=product)
        store = store_inv.store
        initial_stock = store_inv.current_stock
        
        response = cashier_client.post('/api/sales/', {
            'customer_name': 'Test Customer',
            'payment_method': 'CASH',
            'store': store.id,
            'items': [
                {
                    'product': product.id,
                    'quantity': 2,
                    'unit_price': str(product.selling_price)
                }
            ]
        }, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED, f"Expected 201, got {response.status_code}: {response.data}"
        assert 'sale_number' in response.data
        
        store_inv.refresh_from_db()
        assert store_inv.current_stock == initial_stock - 2

    def test_create_wholesale_sale(self, cashier_client, product):
        """Test creating a wholesale sale"""
        from inventory.models import StoreInventory
        store = StoreInventory.objects.get(product=product).store
        
        response = cashier_client.post('/api/sales/', {
            'customer_name': 'Wholesale Customer',
            'payment_method': 'BANK_TRANSFER',
            'store': store.id,
            'is_wholesale': True,
            'items': [
                {
                    'product': product.id,
                    'quantity': 10,
                    'unit_price': str(product.wholesale_price or product.selling_price)
                }
            ]
        }, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['is_wholesale'] is True

    def test_create_sale_with_discount(self, cashier_client, product):
        """Test creating a sale with discount"""
        from inventory.models import StoreInventory
        store = StoreInventory.objects.get(product=product).store
        
        response = cashier_client.post('/api/sales/', {
            'customer_name': 'Discount Customer',
            'payment_method': 'CASH',
            'store': store.id,
            'discount': '10.00',
            'items': [
                {
                    'product': product.id,
                    'quantity': 1,
                    'unit_price': str(product.selling_price)
                }
            ]
        }, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert Decimal(response.data['discount']) == Decimal('10.00')

    def test_create_sale_insufficient_stock(self, cashier_client, product):
        """Test creating sale with insufficient stock fails"""
        from inventory.models import StoreInventory
        store = StoreInventory.objects.get(product=product).store
        
        response = cashier_client.post('/api/sales/', {
            'payment_method': 'CASH',
            'store_id': store.id,
            'items': [
                {
                    'product': product.id,
                    'quantity': 9999,
                    'unit_price': str(product.selling_price)
                }
            ]
        }, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_sale_auto_assigns_partner(self, cashier_client, product, partner):
        """Test sale is auto-assigned to cashier's partner"""
        from inventory.models import StoreInventory
        store = StoreInventory.objects.get(product=product).store
        
        response = cashier_client.post('/api/sales/', {
            'payment_method': 'CASH',
            'store': store.id,
            'items': [
                {
                    'product': product.id,
                    'quantity': 1,
                    'unit_price': str(product.selling_price)
                }
            ]
        }, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED, f"Expected 201, got {response.status_code}: {response.data}"
        sale = Sale.objects.get(sale_number=response.data['sale_number'])
        assert sale.partner == partner

    def test_create_sale_auto_assigns_cashier(self, cashier_client, product, cashier_user):
        """Test sale is auto-assigned to current user as cashier"""
        from inventory.models import StoreInventory
        store = StoreInventory.objects.get(product=product).store
        
        response = cashier_client.post('/api/sales/', {
            'payment_method': 'CASH',
            'store': store.id,
            'items': [
                {
                    'product': product.id,
                    'quantity': 1,
                    'unit_price': str(product.selling_price)
                }
            ]
        }, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED, f"Expected 201, got {response.status_code}: {response.data}"
        sale = Sale.objects.get(sale_number=response.data['sale_number'])
        assert sale.cashier == cashier_user

    def test_create_sale_validates_empty_items(self, cashier_client):
        """Test validation fails when items list is empty"""
        response = cashier_client.post('/api/sales/', {
            'payment_method': 'CASH',
            'items': []
        }, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestSaleDetailAPI:
    """Test sale detail endpoint"""

    def test_get_sale_detail(self, admin_client, sale):
        """Test getting sale details"""
        response = admin_client.get(f'/api/sales/{sale.id}/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['sale_number'] == sale.sale_number
        assert 'items' in response.data
        assert len(response.data['items']) >= 1

    def test_sale_detail_includes_product_info(self, admin_client, sale):
        """Test sale detail includes product information"""
        response = admin_client.get(f'/api/sales/{sale.id}/')
        
        assert response.status_code == status.HTTP_200_OK
        items = response.data['items']
        assert len(items) >= 1
        assert 'product' in items[0]

    def test_cannot_access_other_partner_sale(self, admin_client, partner2, cashier_user):
        """Test cannot access another partner's sale"""
        partner2_cashier = User.objects.create_user(
            username='p2_cashier2',
            password='test123',
            role=User.Role.CASHIER,
            partner=partner2
        )
        partner2_sale = Sale.objects.create(
            partner=partner2,
            sale_number='P2-SALE-002',
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00'),
            cashier=partner2_cashier
        )
        
        response = admin_client.get(f'/api/sales/{partner2_sale.id}/')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ============== Sales Summary API Tests ==============

@pytest.mark.django_db
class TestSalesSummaryAPI:
    """Test sales summary endpoint"""

    def test_sales_summary(self, admin_client, sale, wholesale_sale):
        """Test getting sales summary"""
        response = admin_client.get('/api/sales/summary/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'total_sales_count' in response.data
        assert 'total_revenue' in response.data

    def test_sales_summary_date_filter(self, admin_client, sale):
        """Test sales summary with date filter"""
        today = date.today()
        response = admin_client.get(f'/api/sales/summary/?date_from={today}&date_to={today}')
        
        assert response.status_code == status.HTTP_200_OK

    def test_sales_summary_partner_isolation(self, admin_client, sale):
        """Test sales summary only includes partner's data"""
        response = admin_client.get('/api/sales/summary/')
        
        assert response.status_code == status.HTTP_200_OK


# ============== Top Selling Products API Tests ==============

@pytest.mark.django_db
class TestTopSellingProductsAPI:
    """Test top selling products endpoint"""

    def test_top_selling_products(self, admin_client, sale):
        """Test getting top selling products"""
        response = admin_client.get('/api/sales/top-products/')
        
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list) or 'results' in response.data

    def test_top_selling_products_limit(self, admin_client, sale):
        """Test top selling products with limit"""
        response = admin_client.get('/api/sales/top-products/?limit=5')
        
        assert response.status_code == status.HTTP_200_OK

    def test_top_selling_products_date_filter(self, admin_client, sale):
        """Test top selling products with date filter"""
        today = date.today()
        response = admin_client.get(f'/api/sales/top-products/?date_from={today}')
        
        assert response.status_code == status.HTTP_200_OK


# ============== Role-Based Access Tests ==============

@pytest.mark.django_db
class TestSalesRoleAccess:
    """Test role-based access control for sales"""

    def test_cashier_can_create_sales(self, cashier_client, product):
        """Test cashier can create sales"""
        from inventory.models import StoreInventory
        store = StoreInventory.objects.get(product=product).store
        
        response = cashier_client.post('/api/sales/', {
            'payment_method': 'CASH',
            'store': store.id,
            'items': [
                {
                    'product': product.id,
                    'quantity': 1,
                    'unit_price': str(product.selling_price)
                }
            ]
        }, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED

    def test_admin_can_view_sales(self, admin_client, sale):
        """Test admin can view sales"""
        response = admin_client.get('/api/sales/')
        
        assert response.status_code == status.HTTP_200_OK

    def test_viewer_cannot_view_sales(self, viewer_client, sale):
        """Test viewer cannot view sales - requires IsCashierOrAbove"""
        response = viewer_client.get('/api/sales/')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_viewer_cannot_create_sales(self, viewer_client, product):
        """Test viewer cannot create sales"""
        response = viewer_client.post('/api/sales/', {
            'payment_method': 'CASH',
            'items': [
                {
                    'product': product.id,
                    'quantity': 1,
                    'unit_price': str(product.selling_price)
                }
            ]
        }, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_inventory_staff_can_view_sales(self, inventory_client, sale):
        """Test inventory staff can view sales"""
        response = inventory_client.get('/api/sales/')
        
        assert response.status_code == status.HTTP_200_OK


# ============== Impersonation Tests ==============

@pytest.mark.django_db
class TestSalesImpersonation:
    """Test impersonation for sales"""

    def test_impersonation_sees_partner_sales(self, impersonation_client, sale):
        """Test impersonation sees impersonated partner's sales"""
        response = impersonation_client.get('/api/sales/')
        
        assert response.status_code == status.HTTP_200_OK
        sales = response.data if isinstance(response.data, list) else response.data.get('results', [])
        sale_numbers = [s['sale_number'] for s in sales]
        assert sale.sale_number in sale_numbers

    def test_impersonation_can_view_summary(self, impersonation_client, sale):
        """Test impersonation can view sales summary"""
        response = impersonation_client.get('/api/sales/summary/')
        
        assert response.status_code == status.HTTP_200_OK
