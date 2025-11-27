import pytest
from decimal import Decimal
from inventory.models import Category, Product, Supplier, PurchaseOrder, POItem


@pytest.fixture
def category(db):
    """Create a test category"""
    return Category.objects.create(
        name='Engine Parts',
        description='Engine related components'
    )


@pytest.fixture
def product(db, category):
    """Create a test product"""
    return Product.objects.create(
        sku='ENG-001',
        name='Engine Oil Filter',
        category=category,
        brand='Toyota',
        unit_of_measure='PIECE',
        cost_price=Decimal('10.00'),
        selling_price=Decimal('15.00'),
        minimum_stock_level=10,
        current_stock=50,
        barcode='1234567890'
    )


@pytest.fixture
def supplier(db):
    """Create a test supplier"""
    return Supplier.objects.create(
        name='Parts Supplier Co.',
        contact_person='John Doe',
        email='john@supplier.com',
        phone='123-456-7890'
    )


@pytest.mark.django_db
class TestCategoryModel:
    """Test Category model"""
    
    def test_create_category(self):
        """Test creating a category"""
        category = Category.objects.create(
            name='Electrical',
            description='Electrical components'
        )
        
        assert category.name == 'Electrical'
        assert str(category) == 'Electrical'
    
    def test_category_ordering(self):
        """Test categories are ordered by name"""
        Category.objects.create(name='Zebra')
        Category.objects.create(name='Alpha')
        
        categories = list(Category.objects.all())
        assert categories[0].name == 'Alpha'
        assert categories[1].name == 'Zebra'


@pytest.mark.django_db
class TestProductModel:
    """Test Product model"""
    
    def test_create_product(self, category):
        """Test creating a product"""
        product = Product.objects.create(
            sku='TEST-001',
            name='Test Product',
            category=category,
            cost_price=Decimal('5.00'),
            selling_price=Decimal('10.00'),
            barcode='9876543210'
        )
        
        assert product.sku == 'TEST-001'
        assert product.barcode == '9876543210'
        assert str(product) == 'TEST-001 - Test Product'
    
    def test_product_is_low_stock(self, product):
        """Test low stock detection"""
        product.current_stock = 5
        product.minimum_stock_level = 10
        product.save()
        
        assert product.is_low_stock is True
        
        product.current_stock = 15
        product.save()
        
        assert product.is_low_stock is False
    
    def test_product_stock_value(self, product):
        """Test stock value calculation"""
        product.current_stock = 100
        product.cost_price = Decimal('10.00')
        
        assert product.stock_value == Decimal('1000.00')


@pytest.mark.django_db
class TestSupplierModel:
    """Test Supplier model"""
    
    def test_create_supplier(self):
        """Test creating a supplier"""
        supplier = Supplier.objects.create(
            name='Test Supplier',
            email='supplier@test.com'
        )
        
        assert supplier.name == 'Test Supplier'
        assert str(supplier) == 'Test Supplier'


@pytest.mark.django_db
class TestPurchaseOrderModel:
    """Test PurchaseOrder model"""
    
    def test_create_purchase_order(self, supplier, admin_user):
        """Test creating a purchase order"""
        from datetime import date
        
        po = PurchaseOrder.objects.create(
            po_number='PO-001',
            supplier=supplier,
            order_date=date.today(),
            created_by=admin_user
        )
        
        assert po.po_number == 'PO-001'
        assert po.status == 'DRAFT'
    
    def test_purchase_order_total_amount(self, supplier, admin_user, product):
        """Test PO total amount calculation"""
        from datetime import date
        
        po = PurchaseOrder.objects.create(
            po_number='PO-002',
            supplier=supplier,
            order_date=date.today(),
            created_by=admin_user
        )
        
        POItem.objects.create(
            purchase_order=po,
            product=product,
            ordered_quantity=10,
            unit_cost=Decimal('8.00')
        )
        
        assert po.total_amount == Decimal('80.00')
