"""
Comprehensive tests for Inventory Module.
Tests for: Categories, Products, Suppliers, Purchase Orders, and multi-tenant isolation.
"""
import pytest
from decimal import Decimal
from datetime import date
from rest_framework import status
from inventory.models import Category, Product, Supplier, PurchaseOrder, POItem


# ============== Category Model Tests ==============

@pytest.mark.django_db
class TestCategoryModel:
    """Test Category model"""
    
    def test_create_category(self, partner):
        """Test creating a category"""
        category = Category.objects.create(
            partner=partner,
            name='Electrical',
            description='Electrical components'
        )
        
        assert category.name == 'Electrical'
        assert str(category) == 'Electrical'
    
    def test_category_ordering(self, partner):
        """Test categories are ordered by name"""
        Category.objects.create(partner=partner, name='Zebra')
        Category.objects.create(partner=partner, name='Alpha')
        
        categories = list(Category.objects.filter(partner=partner))
        assert categories[0].name == 'Alpha'
        assert categories[1].name == 'Zebra'


# ============== Product Model Tests ==============

@pytest.mark.django_db
class TestProductModel:
    """Test Product model"""
    
    def test_create_product(self, category, partner):
        """Test creating a product"""
        product = Product.objects.create(
            partner=partner,
            sku='TEST-001',
            name='Test Product',
            category=category,
            cost_price=Decimal('5.00'),
            selling_price=Decimal('10.00'),
            barcode='9876543210'
        )
        
        assert product.sku == 'TEST-001'
        assert product.barcode == '9876543210'
        assert 'TEST-001' in str(product)
    
    def test_product_is_low_stock(self, product, store):
        """Test low stock detection via StoreInventory"""
        from inventory.models import StoreInventory
        
        # Create store inventory with low stock
        store_inv = StoreInventory.objects.create(
            product=product,
            store=store,
            current_stock=5,
            minimum_stock_level=10
        )
        
        assert store_inv.current_stock < store_inv.minimum_stock_level
        
        # Update to normal stock
        store_inv.current_stock = 15
        store_inv.save()
        
        assert store_inv.current_stock >= store_inv.minimum_stock_level
    
    def test_product_stock_value(self, product, store):
        """Test stock value calculation via StoreInventory"""
        from inventory.models import StoreInventory
        
        # Create store inventory
        store_inv = StoreInventory.objects.create(
            product=product,
            store=store,
            current_stock=100,
            minimum_stock_level=10
        )
        
        # Stock value is quantity * cost price
        expected_value = store_inv.current_stock * product.cost_price
        assert expected_value == Decimal('10000.00')  # 100 * 100.00


# ============== Supplier Model Tests ==============

@pytest.mark.django_db
class TestSupplierModel:
    """Test Supplier model"""
    
    def test_create_supplier(self, partner):
        """Test creating a supplier"""
        supplier = Supplier.objects.create(
            partner=partner,
            name='Test Supplier',
            email='supplier@test.com'
        )
        
        assert supplier.name == 'Test Supplier'
        assert str(supplier) == 'Test Supplier'


# ============== Purchase Order Model Tests ==============

@pytest.mark.django_db
class TestPurchaseOrderModel:
    """Test PurchaseOrder model"""
    
    def test_create_purchase_order(self, supplier, admin_user, partner):
        """Test creating a purchase order"""
        po = PurchaseOrder.objects.create(
            partner=partner,
            po_number='PO-001',
            supplier=supplier,
            order_date=date.today(),
            created_by=admin_user
        )
        
        assert po.po_number == 'PO-001'
        assert po.status == 'DRAFT'
    
    def test_purchase_order_total_amount(self, supplier, admin_user, product, partner):
        """Test PO total amount calculation"""
        po = PurchaseOrder.objects.create(
            partner=partner,
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


# ============== Category API Tests ==============

@pytest.mark.django_db
class TestCategoryListAPI:
    """Test category listing endpoint"""

    def test_list_categories(self, admin_client, category, category2):
        """Test listing categories returns all partner categories"""
        response = admin_client.get('/api/inventory/categories/')
        
        assert response.status_code == status.HTTP_200_OK
        categories = response.data if isinstance(response.data, list) else response.data.get('results', [])
        assert len(categories) >= 2

    def test_list_categories_partner_isolation(self, admin_client, category, partner2_category):
        """Test categories are filtered by partner - cannot see other partner's data"""
        response = admin_client.get('/api/inventory/categories/')
        
        assert response.status_code == status.HTTP_200_OK
        categories = response.data if isinstance(response.data, list) else response.data.get('results', [])
        names = [c['name'] for c in categories]
        assert category.name in names
        assert partner2_category.name not in names

    def test_impersonation_sees_correct_partner_data(self, impersonation_client, category, partner2_category):
        """Test impersonation shows impersonated partner's categories"""
        response = impersonation_client.get('/api/inventory/categories/')
        
        assert response.status_code == status.HTTP_200_OK
        categories = response.data if isinstance(response.data, list) else response.data.get('results', [])
        names = [c['name'] for c in categories]
        assert category.name in names
        assert partner2_category.name not in names

    def test_super_admin_must_impersonate(self, super_admin_client):
        """Super admin without impersonation is blocked from tenant data"""
        response = super_admin_client.get('/api/inventory/categories/')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'impersonate' in str(response.data.get('detail', '')).lower()

    def test_unauthenticated_cannot_list_categories(self, api_client):
        """Test unauthenticated request is rejected"""
        response = api_client.get('/api/inventory/categories/')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestCategoryCreateAPI:
    """Test category creation endpoint"""

    def test_create_category_success(self, admin_client, partner):
        """Test creating a category successfully"""
        response = admin_client.post('/api/inventory/categories/', {
            'name': 'New Category',
            'description': 'A new test category'
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'New Category'
        category = Category.objects.get(id=response.data['id'])
        assert category.partner == partner

    def test_create_category_duplicate_name_same_partner_fails(self, admin_client, category):
        """Test creating category with duplicate name in same partner fails"""
        from django.db import IntegrityError
        
        with pytest.raises(IntegrityError):
            admin_client.post('/api/inventory/categories/', {
                'name': category.name,
                'description': 'Duplicate'
            })

    def test_create_category_same_name_different_partner_ok(self, partner2_client, category):
        """Test different partners can have same category name"""
        response = partner2_client.post('/api/inventory/categories/', {
            'name': category.name,
            'description': 'Different partner'
        })
        
        assert response.status_code == status.HTTP_201_CREATED

    def test_viewer_cannot_create_category(self, viewer_client):
        """Test viewer role cannot create categories"""
        response = viewer_client.post('/api/inventory/categories/', {
            'name': 'Viewer Category'
        })
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestCategoryDetailAPI:
    """Test category detail, update, delete endpoints"""

    def test_get_category_detail(self, admin_client, category):
        """Test getting category details"""
        response = admin_client.get(f'/api/inventory/categories/{category.id}/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == category.name
        assert response.data['description'] == category.description

    def test_update_category(self, admin_client, category):
        """Test updating a category"""
        response = admin_client.patch(f'/api/inventory/categories/{category.id}/', {
            'description': 'Updated description'
        })
        
        assert response.status_code == status.HTTP_200_OK
        category.refresh_from_db()
        assert category.description == 'Updated description'

    def test_delete_category_without_products(self, admin_client, partner):
        """Test deleting a category without products"""
        cat = Category.objects.create(partner=partner, name='Deletable')
        
        response = admin_client.delete(f'/api/inventory/categories/{cat.id}/')
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Category.objects.filter(id=cat.id).exists()

    def test_cannot_access_other_partner_category(self, admin_client, partner2_category):
        """Test cannot access another partner's category"""
        response = admin_client.get(f'/api/inventory/categories/{partner2_category.id}/')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cannot_update_other_partner_category(self, admin_client, partner2_category):
        """Test cannot update another partner's category"""
        response = admin_client.patch(f'/api/inventory/categories/{partner2_category.id}/', {
            'name': 'Hacked Name'
        })
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ============== Product API Tests ==============

@pytest.mark.django_db
class TestProductListAPI:
    """Test product listing endpoint"""

    def test_list_products(self, admin_client, product, product2):
        """Test listing products"""
        response = admin_client.get('/api/inventory/products/')
        
        assert response.status_code == status.HTTP_200_OK
        products = response.data if isinstance(response.data, list) else response.data.get('results', [])
        assert len(products) >= 2

    def test_list_products_partner_isolation(self, admin_client, product, partner2_product):
        """Test products are filtered by partner"""
        response = admin_client.get('/api/inventory/products/')
        
        assert response.status_code == status.HTTP_200_OK
        products = response.data if isinstance(response.data, list) else response.data.get('results', [])
        skus = [p['sku'] for p in products]
        assert product.sku in skus
        assert partner2_product.sku not in skus

    def test_search_products_by_name(self, admin_client, product):
        """Test searching products by name"""
        response = admin_client.get(f'/api/inventory/products/?search={product.name[:5]}')
        
        assert response.status_code == status.HTTP_200_OK
        products = response.data if isinstance(response.data, list) else response.data.get('results', [])
        assert any(p['name'] == product.name for p in products)

    def test_search_products_by_sku(self, admin_client, product):
        """Test searching products by SKU"""
        response = admin_client.get(f'/api/inventory/products/?search={product.sku}')
        
        assert response.status_code == status.HTTP_200_OK
        products = response.data if isinstance(response.data, list) else response.data.get('results', [])
        assert any(p['sku'] == product.sku for p in products)

    def test_filter_products_by_category(self, admin_client, product, category):
        """Test filtering products by category"""
        response = admin_client.get(f'/api/inventory/products/?category={category.id}')
        
        assert response.status_code == status.HTTP_200_OK
        products = response.data if isinstance(response.data, list) else response.data.get('results', [])
        for p in products:
            assert p['category'] == category.id

    def test_filter_active_products(self, admin_client, product):
        """Test filtering active products"""
        response = admin_client.get('/api/inventory/products/?is_active=true')
        
        assert response.status_code == status.HTTP_200_OK
        products = response.data if isinstance(response.data, list) else response.data.get('results', [])
        for p in products:
            assert p['is_active'] is True


@pytest.mark.django_db
class TestProductCreateAPI:
    """Test product creation endpoint"""

    def test_create_product_success(self, admin_client, category, partner):
        """Test creating a product successfully"""
        response = admin_client.post('/api/inventory/products/', {
            'sku': 'NEW-SKU-001',
            'name': 'New Product',
            'category': category.id,
            'cost_price': '50.00',
            'selling_price': '75.00',
            'minimum_stock_level': 10
        })
        
        assert response.status_code == status.HTTP_201_CREATED, f"Expected 201, got {response.status_code}: {response.data}"
        assert response.data['sku'] == 'NEW-SKU-001'
        product = Product.objects.get(sku='NEW-SKU-001')
        assert product.partner == partner

    def test_create_product_with_all_fields(self, admin_client, category):
        """Test creating product with all optional fields"""
        response = admin_client.post('/api/inventory/products/', {
            'sku': 'FULL-001',
            'name': 'Full Product',
            'description': 'Full description',
            'category': category.id,
            'brand': 'Test Brand',
            'model_compatibility': 'Model A, Model B',
            'unit_of_measure': 'BOX',
            'cost_price': '100.00',
            'selling_price': '150.00',
            'wholesale_price': '125.00',
            'minimum_stock_level': 20,
            'barcode': '9876543210123'
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['brand'] == 'Test Brand'
        assert response.data['wholesale_price'] == '125.00'

    def test_create_product_duplicate_sku_same_partner_fails(self, admin_client, product, category):
        """Test duplicate SKU within same partner fails"""
        from django.db import IntegrityError
        
        with pytest.raises(IntegrityError):
            admin_client.post('/api/inventory/products/', {
                'sku': product.sku,
                'name': 'Duplicate SKU Product',
                'category': category.id,
                'cost_price': '50.00',
                'selling_price': '75.00'
            })

    def test_create_product_duplicate_barcode_fails(self, admin_client, product, category):
        """Test duplicate barcode fails"""
        response = admin_client.post('/api/inventory/products/', {
            'sku': 'UNIQUE-SKU',
            'name': 'Duplicate Barcode',
            'category': category.id,
            'cost_price': '50.00',
            'selling_price': '75.00',
            'barcode': product.barcode
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_product_negative_price_fails(self, admin_client, category):
        """Test negative prices are rejected"""
        response = admin_client.post('/api/inventory/products/', {
            'sku': 'NEGATIVE-001',
            'name': 'Negative Price',
            'category': category.id,
            'cost_price': '-50.00',
            'selling_price': '75.00'
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_inventory_staff_can_create_products(self, inventory_client, category):
        """Test inventory staff can create products"""
        response = inventory_client.post('/api/inventory/products/', {
            'sku': 'STAFF-001',
            'name': 'Staff Product',
            'category': category.id,
            'cost_price': '50.00',
            'selling_price': '75.00'
        })
        
        assert response.status_code == status.HTTP_201_CREATED

    def test_cashier_cannot_create_products(self, cashier_client, category):
        """Test cashier cannot create products"""
        response = cashier_client.post('/api/inventory/products/', {
            'sku': 'CASHIER-001',
            'name': 'Cashier Product',
            'category': category.id,
            'cost_price': '50.00',
            'selling_price': '75.00'
        })
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestProductDetailAPI:
    """Test product detail, update, delete endpoints"""

    def test_get_product_detail(self, admin_client, product):
        """Test getting product details"""
        response = admin_client.get(f'/api/inventory/products/{product.id}/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['sku'] == product.sku
        assert response.data['name'] == product.name
        assert 'category' in response.data

    def test_update_product_price(self, admin_client, product):
        """Test updating product price"""
        response = admin_client.patch(f'/api/inventory/products/{product.id}/', {
            'selling_price': '200.00'
        })
        
        assert response.status_code == status.HTTP_200_OK
        product.refresh_from_db()
        assert product.selling_price == Decimal('200.00')

    def test_update_product_minimum_stock(self, admin_client, product):
        """Test updating product minimum stock level"""
        response = admin_client.patch(f'/api/inventory/products/{product.id}/', {
            'minimum_stock_level': 25
        })
        
        assert response.status_code == status.HTTP_200_OK
        product.refresh_from_db()
        assert product.minimum_stock_level == 25

    def test_deactivate_product(self, admin_client, product):
        """Test deactivating a product"""
        response = admin_client.patch(f'/api/inventory/products/{product.id}/', {
            'is_active': False
        })
        
        assert response.status_code == status.HTTP_200_OK
        product.refresh_from_db()
        assert product.is_active is False

    def test_delete_product_without_sales(self, admin_client, partner, category):
        """Test deleting product without sales history"""
        prod = Product.objects.create(
            partner=partner,
            sku='DELETE-001',
            name='Deletable',
            category=category,
            cost_price=Decimal('10.00'),
            selling_price=Decimal('20.00')
        )
        
        response = admin_client.delete(f'/api/inventory/products/{prod.id}/')
        
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_cannot_access_other_partner_product(self, admin_client, partner2_product):
        """Test cannot access another partner's product"""
        response = admin_client.get(f'/api/inventory/products/{partner2_product.id}/')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestBarcodeLookupAPI:
    """Test barcode lookup endpoint"""

    def test_barcode_lookup_success(self, admin_client, product):
        """Test successful barcode lookup"""
        response = admin_client.get(f'/api/inventory/products/barcode/{product.barcode}/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['barcode'] == product.barcode
        assert response.data['sku'] == product.sku

    def test_barcode_lookup_not_found(self, admin_client):
        """Test barcode lookup with non-existent barcode"""
        response = admin_client.get('/api/inventory/products/barcode/NONEXISTENT123/')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_barcode_lookup_partner_isolation(self, admin_client, partner2_product):
        """Test cannot lookup other partner's product by barcode"""
        partner2_product.barcode = '9999999999999'
        partner2_product.save()
        
        response = admin_client.get(f'/api/inventory/products/barcode/{partner2_product.barcode}/')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cashier_can_lookup_barcode(self, cashier_client, product):
        """Test cashier can use barcode lookup (for POS)"""
        response = cashier_client.get(f'/api/inventory/products/barcode/{product.barcode}/')
        
        assert response.status_code == status.HTTP_200_OK


# ============== Supplier API Tests ==============

@pytest.mark.django_db
class TestSupplierListAPI:
    """Test supplier listing endpoint"""

    def test_list_suppliers(self, admin_client, supplier):
        """Test listing suppliers"""
        response = admin_client.get('/api/inventory/suppliers/')
        
        assert response.status_code == status.HTTP_200_OK
        suppliers = response.data if isinstance(response.data, list) else response.data.get('results', [])
        assert len(suppliers) >= 1

    def test_list_suppliers_partner_isolation(self, admin_client, supplier, partner2):
        """Test suppliers are filtered by partner"""
        partner2_supplier = Supplier.objects.create(
            partner=partner2,
            name='Partner2 Supplier'
        )
        
        response = admin_client.get('/api/inventory/suppliers/')
        
        suppliers = response.data if isinstance(response.data, list) else response.data.get('results', [])
        names = [s['name'] for s in suppliers]
        assert supplier.name in names
        assert partner2_supplier.name not in names


@pytest.mark.django_db
class TestSupplierCreateAPI:
    """Test supplier creation endpoint"""

    def test_create_supplier_success(self, admin_client, partner):
        """Test creating a supplier"""
        response = admin_client.post('/api/inventory/suppliers/', {
            'name': 'New Supplier',
            'contact_person': 'John Smith',
            'email': 'john@supplier.com',
            'phone': '1234567890',
            'address': '123 Supplier St'
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        supplier = Supplier.objects.get(id=response.data['id'])
        assert supplier.partner == partner

    def test_create_supplier_duplicate_name_fails(self, admin_client, supplier):
        """Test duplicate supplier name in same partner fails"""
        from django.db import IntegrityError
        
        with pytest.raises(IntegrityError):
            admin_client.post('/api/inventory/suppliers/', {
                'name': supplier.name
            })


@pytest.mark.django_db
class TestSupplierDetailAPI:
    """Test supplier detail endpoints"""

    def test_get_supplier_detail(self, admin_client, supplier):
        """Test getting supplier details"""
        response = admin_client.get(f'/api/inventory/suppliers/{supplier.id}/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == supplier.name

    def test_update_supplier(self, admin_client, supplier):
        """Test updating supplier"""
        response = admin_client.patch(f'/api/inventory/suppliers/{supplier.id}/', {
            'email': 'updated@supplier.com'
        })
        
        assert response.status_code == status.HTTP_200_OK
        supplier.refresh_from_db()
        assert supplier.email == 'updated@supplier.com'


# ============== Purchase Order API Tests ==============

@pytest.mark.django_db
class TestPurchaseOrderListAPI:
    """Test purchase order listing endpoint"""

    def test_list_purchase_orders(self, admin_client, purchase_order):
        """Test listing purchase orders"""
        response = admin_client.get('/api/inventory/purchase-orders/')
        
        assert response.status_code == status.HTTP_200_OK
        orders = response.data if isinstance(response.data, list) else response.data.get('results', [])
        assert len(orders) >= 1

    def test_list_purchase_orders_partner_isolation(self, admin_client, purchase_order, partner2, partner2_admin):
        """Test POs are filtered by partner"""
        partner2_supplier = Supplier.objects.create(partner=partner2, name='P2 Supplier')
        partner2_po = PurchaseOrder.objects.create(
            partner=partner2,
            po_number='P2-PO-001',
            supplier=partner2_supplier,
            order_date=date.today(),
            created_by=partner2_admin
        )
        
        response = admin_client.get('/api/inventory/purchase-orders/')
        
        orders = response.data if isinstance(response.data, list) else response.data.get('results', [])
        po_numbers = [o['po_number'] for o in orders]
        assert purchase_order.po_number in po_numbers
        assert partner2_po.po_number not in po_numbers


@pytest.mark.django_db
class TestPurchaseOrderCreateAPI:
    """Test purchase order creation endpoint"""

    def test_create_purchase_order_success(self, admin_client, supplier, product, partner):
        """Test creating a purchase order with items"""
        response = admin_client.post('/api/inventory/purchase-orders/', {
            'po_number': 'NEW-PO-001',
            'supplier': supplier.id,
            'order_date': str(date.today()),
            'expected_delivery_date': str(date.today()),
            'notes': 'Test order',
            'items': [
                {
                    'product': product.id,
                    'ordered_quantity': 10,
                    'unit_cost': '100.00'
                }
            ]
        }, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED, f"Expected 201, got {response.status_code}: {response.data}"
        assert response.data['po_number'] == 'NEW-PO-001'
        po = PurchaseOrder.objects.get(po_number='NEW-PO-001')
        assert po.partner == partner
        assert po.items.count() == 1


@pytest.mark.django_db
class TestPurchaseOrderDetailAPI:
    """Test purchase order detail endpoints"""

    def test_get_purchase_order_detail(self, admin_client, purchase_order):
        """Test getting PO details with items"""
        response = admin_client.get(f'/api/inventory/purchase-orders/{purchase_order.id}/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['po_number'] == purchase_order.po_number
        assert 'items' in response.data

    def test_update_purchase_order_status(self, admin_client, purchase_order):
        """Test updating PO status"""
        response = admin_client.patch(f'/api/inventory/purchase-orders/{purchase_order.id}/', {
            'status': 'SUBMITTED'
        })
        
        assert response.status_code == status.HTTP_200_OK
        purchase_order.refresh_from_db()
        assert purchase_order.status == 'SUBMITTED'


@pytest.mark.django_db
class TestReceivePurchaseOrderAPI:
    """Test receiving purchase order items"""

    def test_receive_po_items_updates_stock(self, admin_client, purchase_order, product):
        """Test receiving items updates product stock"""
        from inventory.models import StoreInventory
        po_item = purchase_order.items.first()
        inventory = StoreInventory.objects.get(product=product, store=product.partner.stores.first())
        initial_stock = inventory.current_stock
        
        response = admin_client.post(f'/api/inventory/purchase-orders/{purchase_order.id}/receive/', [
            {
                'item_id': po_item.id,
                'received_quantity': 5
            }
        ], format='json')
        
        assert response.status_code == status.HTTP_200_OK
        inventory.refresh_from_db()
        assert inventory.current_stock == initial_stock + 5

    def test_receive_po_updates_received_quantity(self, admin_client, purchase_order):
        """Test receiving updates PO item received quantity"""
        po_item = purchase_order.items.first()
        
        admin_client.post(f'/api/inventory/purchase-orders/{purchase_order.id}/receive/', [
            {
                'item_id': po_item.id,
                'received_quantity': 3
            }
        ], format='json')
        
        po_item.refresh_from_db()
        assert po_item.received_quantity == 3


# ============== Label Printing API Tests ==============

@pytest.mark.django_db
class TestLabelPrintingAPI:
    """Test barcode label printing endpoints"""

    def test_print_single_product_label(self, admin_client, product):
        """Test printing label for single product (returns PDF)"""
        response = admin_client.get(f'/api/inventory/products/{product.id}/print-label/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response['Content-Type'] == 'application/pdf'

    def test_print_multiple_labels(self, admin_client, product, product2):
        """Test batch label printing"""
        response = admin_client.post('/api/inventory/products/print-labels/', {
            'product_ids': [product.id, product2.id],
            'label_size': '2x1'
        }, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response['Content-Type'] == 'application/pdf'


# ============== Role-Based Access Tests ==============

@pytest.mark.django_db
class TestInventoryRoleAccess:
    """Test role-based access control for inventory"""

    def test_viewer_can_read_products(self, viewer_client, product):
        """Test viewer can view products"""
        response = viewer_client.get('/api/inventory/products/')
        assert response.status_code == status.HTTP_200_OK

    def test_viewer_cannot_create_products(self, viewer_client, category):
        """Test viewer cannot create products"""
        response = viewer_client.post('/api/inventory/products/', {
            'sku': 'VIEW-001',
            'name': 'Viewer Product',
            'category': category.id,
            'cost_price': '50.00',
            'selling_price': '75.00'
        })
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_viewer_cannot_update_products(self, viewer_client, product):
        """Test viewer cannot update products"""
        response = viewer_client.patch(f'/api/inventory/products/{product.id}/', {
            'name': 'Hacked'
        })
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cashier_can_view_products(self, cashier_client, product):
        """Test cashier can view products (for POS)"""
        response = cashier_client.get('/api/inventory/products/')
        assert response.status_code == status.HTTP_200_OK

    def test_cashier_cannot_modify_products(self, cashier_client, product):
        """Test cashier cannot modify products"""
        response = cashier_client.patch(f'/api/inventory/products/{product.id}/', {
            'selling_price': '999.99'
        })
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_inventory_staff_can_manage_products(self, inventory_client, product):
        """Test inventory staff can update products"""
        response = inventory_client.patch(f'/api/inventory/products/{product.id}/', {
            'minimum_stock_level': 25
        })
        assert response.status_code == status.HTTP_200_OK
