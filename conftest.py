"""
Pytest fixtures for POS API tests.
Provides common test data and utilities for all test modules.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from oauth2_provider.models import Application, AccessToken
from oauthlib.common import generate_token
from django.utils import timezone

User = get_user_model()


# ============== OAuth2 Application Fixture ==============

@pytest.fixture
def oauth_application(db):
    """Create OAuth2 application for testing - must match the name used in views"""
    return Application.objects.create(
        name='pos-frontend',  # Must match the name used in login_view and impersonate_partner
        client_type=Application.CLIENT_PUBLIC,
        authorization_grant_type=Application.GRANT_PASSWORD,
    )


# ============== Partner Fixtures ==============

@pytest.fixture
def partner(db):
    """Create a test partner"""
    from users.models import Partner
    return Partner.objects.create(
        name='Test Partner',
        code='TEST001',
        contact_email='partner@test.com',
        contact_phone='1234567890',
        is_active=True
    )


@pytest.fixture
def partner2(db):
    """Create a second test partner for isolation tests"""
    from users.models import Partner
    return Partner.objects.create(
        name='Second Partner',
        code='TEST002',
        contact_email='partner2@test.com',
        is_active=True
    )


@pytest.fixture
def inactive_partner(db):
    """Create an inactive partner"""
    from users.models import Partner
    return Partner.objects.create(
        name='Inactive Partner',
        code='INACTIVE001',
        is_active=False
    )


# ============== User Fixtures ==============

@pytest.fixture
def super_admin(db, oauth_application):
    """Create a super admin user (no partner)"""
    user = User.objects.create_user(
        username='superadmin',
        email='superadmin@test.com',
        password='testpass123',
        role=User.Role.ADMIN,
        is_super_admin=True,
        partner=None
    )
    return user


@pytest.fixture
def admin_user(db, partner, oauth_application):
    """Create an admin user belonging to a partner"""
    user = User.objects.create_user(
        username='admin',
        email='admin@test.com',
        password='testpass123',
        role=User.Role.ADMIN,
        partner=partner
    )
    return user


@pytest.fixture
def inventory_staff_user(db, partner, oauth_application):
    """Create an inventory staff user"""
    user = User.objects.create_user(
        username='inventory_staff',
        email='inventory@test.com',
        password='testpass123',
        role=User.Role.INVENTORY_STAFF,
        partner=partner
    )
    return user


@pytest.fixture
def cashier_user(db, partner, oauth_application):
    """Create a cashier user"""
    user = User.objects.create_user(
        username='cashier',
        email='cashier@test.com',
        password='testpass123',
        role=User.Role.CASHIER,
        partner=partner
    )
    return user


@pytest.fixture
def viewer_user(db, partner, oauth_application):
    """Create a viewer user"""
    user = User.objects.create_user(
        username='viewer',
        email='viewer@test.com',
        password='testpass123',
        role=User.Role.VIEWER,
        partner=partner
    )
    return user


@pytest.fixture
def partner2_admin(db, partner2, oauth_application):
    """Create an admin user for partner2"""
    user = User.objects.create_user(
        username='partner2_admin',
        email='admin2@test.com',
        password='testpass123',
        role=User.Role.ADMIN,
        partner=partner2
    )
    return user


# ============== Token Fixtures ==============

def create_access_token(user, application, scope='read write'):
    """Helper function to create access token"""
    expires = timezone.now() + timedelta(hours=1)
    return AccessToken.objects.create(
        user=user,
        application=application,
        token=generate_token(),
        expires=expires,
        scope=scope
    )


@pytest.fixture
def super_admin_token(super_admin, oauth_application):
    """Create access token for super admin"""
    return create_access_token(super_admin, oauth_application)


@pytest.fixture
def admin_token(admin_user, oauth_application):
    """Create access token for admin"""
    return create_access_token(admin_user, oauth_application)


@pytest.fixture
def inventory_staff_token(inventory_staff_user, oauth_application):
    """Create access token for inventory staff"""
    return create_access_token(inventory_staff_user, oauth_application)


@pytest.fixture
def cashier_token(cashier_user, oauth_application):
    """Create access token for cashier"""
    return create_access_token(cashier_user, oauth_application)


@pytest.fixture
def viewer_token(viewer_user, oauth_application):
    """Create access token for viewer"""
    return create_access_token(viewer_user, oauth_application)


@pytest.fixture
def partner2_admin_token(partner2_admin, oauth_application):
    """Create access token for partner2 admin"""
    return create_access_token(partner2_admin, oauth_application)


@pytest.fixture
def impersonation_token(super_admin, partner, oauth_application):
    """Create impersonation token for super admin impersonating a partner"""
    return create_access_token(
        super_admin, 
        oauth_application, 
        scope=f'read write impersonating:{partner.id}'
    )


# ============== API Client Fixtures ==============

@pytest.fixture
def api_client():
    """Create API test client"""
    return APIClient()


@pytest.fixture
def super_admin_client(api_client, super_admin_token):
    """API client authenticated as super admin"""
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {super_admin_token.token}')
    return api_client


@pytest.fixture
def admin_client(api_client, admin_token):
    """API client authenticated as admin"""
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {admin_token.token}')
    return api_client


@pytest.fixture
def inventory_client(api_client, inventory_staff_token):
    """API client authenticated as inventory staff"""
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {inventory_staff_token.token}')
    return api_client


@pytest.fixture
def cashier_client(api_client, cashier_token):
    """API client authenticated as cashier"""
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {cashier_token.token}')
    return api_client


@pytest.fixture
def viewer_client(api_client, viewer_token):
    """API client authenticated as viewer"""
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {viewer_token.token}')
    return api_client


@pytest.fixture
def partner2_client(api_client, partner2_admin_token):
    """API client authenticated as partner2 admin"""
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {partner2_admin_token.token}')
    return api_client


@pytest.fixture
def impersonation_client(api_client, impersonation_token):
    """API client with impersonation token"""
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {impersonation_token.token}')
    return api_client


# ============== Inventory Fixtures ==============

@pytest.fixture
def category(db, partner):
    """Create a test category"""
    from inventory.models import Category
    return Category.objects.create(
        partner=partner,
        name='Test Category',
        description='Test category description'
    )


@pytest.fixture
def category2(db, partner):
    """Create a second test category"""
    from inventory.models import Category
    return Category.objects.create(
        partner=partner,
        name='Second Category',
        description='Second category description'
    )


@pytest.fixture
def partner2_category(db, partner2):
    """Create a category for partner2"""
    from inventory.models import Category
    return Category.objects.create(
        partner=partner2,
        name='Partner2 Category',
        description='Category for partner 2'
    )


@pytest.fixture
def product(db, partner, category):
    """Create a test product"""
    from inventory.models import Product
    return Product.objects.create(
        partner=partner,
        sku='TEST-SKU-001',
        name='Test Product',
        description='Test product description',
        category=category,
        brand='Test Brand',
        cost_price=Decimal('100.00'),
        selling_price=Decimal('150.00'),
        wholesale_price=Decimal('120.00'),
        minimum_stock_level=10,
        current_stock=50,
        barcode='1234567890123',
        is_active=True
    )


@pytest.fixture
def product2(db, partner, category):
    """Create a second test product"""
    from inventory.models import Product
    return Product.objects.create(
        partner=partner,
        sku='TEST-SKU-002',
        name='Second Product',
        description='Second product description',
        category=category,
        cost_price=Decimal('200.00'),
        selling_price=Decimal('300.00'),
        minimum_stock_level=5,
        current_stock=20,
        barcode='1234567890124',
        is_active=True
    )


@pytest.fixture
def low_stock_product(db, partner, category):
    """Create a product with low stock"""
    from inventory.models import Product
    return Product.objects.create(
        partner=partner,
        sku='LOW-STOCK-001',
        name='Low Stock Product',
        category=category,
        cost_price=Decimal('50.00'),
        selling_price=Decimal('75.00'),
        minimum_stock_level=20,
        current_stock=5,
        is_active=True
    )


@pytest.fixture
def partner2_product(db, partner2, partner2_category):
    """Create a product for partner2"""
    from inventory.models import Product
    return Product.objects.create(
        partner=partner2,
        sku='P2-SKU-001',
        name='Partner2 Product',
        category=partner2_category,
        cost_price=Decimal('80.00'),
        selling_price=Decimal('120.00'),
        current_stock=30,
        is_active=True
    )


@pytest.fixture
def supplier(db, partner):
    """Create a test supplier"""
    from inventory.models import Supplier
    return Supplier.objects.create(
        partner=partner,
        name='Test Supplier',
        contact_person='John Doe',
        email='supplier@test.com',
        phone='9876543210',
        is_active=True
    )


@pytest.fixture
def purchase_order(db, partner, supplier, product, admin_user):
    """Create a test purchase order"""
    from inventory.models import PurchaseOrder, POItem
    po = PurchaseOrder.objects.create(
        partner=partner,
        po_number='PO-001',
        supplier=supplier,
        status='DRAFT',
        order_date=date.today(),
        created_by=admin_user
    )
    POItem.objects.create(
        purchase_order=po,
        product=product,
        ordered_quantity=10,
        unit_cost=Decimal('100.00')
    )
    return po


# ============== Sales Fixtures ==============

@pytest.fixture
def sale(db, partner, product, cashier_user):
    """Create a test sale"""
    from sales.models import Sale, SaleItem
    sale_obj = Sale.objects.create(
        partner=partner,
        sale_number='SALE-001',
        customer_name='Test Customer',
        payment_method='CASH',
        subtotal=Decimal('150.00'),
        discount=Decimal('0.00'),
        total_amount=Decimal('150.00'),
        cashier=cashier_user
    )
    SaleItem.objects.create(
        sale=sale_obj,
        product=product,
        quantity=1,
        unit_price=Decimal('150.00'),
        discount=Decimal('0.00'),
        line_total=Decimal('150.00')
    )
    return sale_obj


@pytest.fixture
def wholesale_sale(db, partner, product, cashier_user):
    """Create a wholesale sale"""
    from sales.models import Sale, SaleItem
    sale_obj = Sale.objects.create(
        partner=partner,
        sale_number='SALE-002',
        customer_name='Wholesale Customer',
        payment_method='BANK_TRANSFER',
        is_wholesale=True,
        subtotal=Decimal('1200.00'),
        discount=Decimal('100.00'),
        total_amount=Decimal('1100.00'),
        cashier=cashier_user
    )
    SaleItem.objects.create(
        sale=sale_obj,
        product=product,
        quantity=10,
        unit_price=Decimal('120.00'),
        discount=Decimal('0.00'),
        line_total=Decimal('1200.00')
    )
    return sale_obj


# ============== Expense Fixtures ==============

@pytest.fixture
def expense_category(db, partner):
    """Create a test expense category"""
    from expenses.models import ExpenseCategory
    return ExpenseCategory.objects.create(
        partner=partner,
        name='Utilities',
        description='Utility expenses',
        color='#3B82F6',
        is_active=True
    )


@pytest.fixture
def expense_category2(db, partner):
    """Create a second expense category"""
    from expenses.models import ExpenseCategory
    return ExpenseCategory.objects.create(
        partner=partner,
        name='Supplies',
        description='Office supplies',
        color='#10B981',
        is_active=True
    )


@pytest.fixture
def expense(db, partner, expense_category, admin_user):
    """Create a test expense"""
    from expenses.models import Expense
    return Expense.objects.create(
        partner=partner,
        title='Electricity Bill',
        description='Monthly electricity',
        amount=Decimal('5000.00'),
        category=expense_category,
        payment_method='BANK_TRANSFER',
        expense_date=date.today(),
        vendor='Power Company',
        created_by=admin_user
    )


@pytest.fixture
def expense2(db, partner, expense_category2, admin_user):
    """Create a second expense"""
    from expenses.models import Expense
    return Expense.objects.create(
        partner=partner,
        title='Office Supplies',
        description='Pens and paper',
        amount=Decimal('500.00'),
        category=expense_category2,
        payment_method='CASH',
        expense_date=date.today() - timedelta(days=7),
        created_by=admin_user
    )


# ============== Stock Fixtures ==============

@pytest.fixture
def stock_transaction(db, partner, product, admin_user):
    """Create a test stock transaction"""
    from stock.models import StockTransaction
    return StockTransaction.objects.create(
        partner=partner,
        product=product,
        transaction_type='IN',
        reason='PURCHASE',
        quantity=10,
        quantity_before=40,
        quantity_after=50,
        unit_cost=Decimal('100.00'),
        total_cost=Decimal('1000.00'),
        reference_number='PO-001',
        performed_by=admin_user
    )


@pytest.fixture
def stock_out_transaction(db, partner, product, cashier_user):
    """Create a stock out transaction"""
    from stock.models import StockTransaction
    return StockTransaction.objects.create(
        partner=partner,
        product=product,
        transaction_type='OUT',
        reason='SALE',
        quantity=5,
        quantity_before=50,
        quantity_after=45,
        reference_number='SALE-001',
        performed_by=cashier_user
    )
