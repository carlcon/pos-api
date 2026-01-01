"""
Django management command to load demo data for POS application.
Creates initial partner, stores, categories, products, and other demo data.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal


class Command(BaseCommand):
    help = 'Load demo data for POS application (partner, stores, products, etc.)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before loading demo data',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        from users.models import Partner, User
        from stores.models import Store
        from inventory.models import Category, Product, Supplier, StoreInventory
        from expenses.models import ExpenseCategory

        self.stdout.write(self.style.NOTICE('Loading demo data...'))

        # =================================================================
        # Create Demo Partner
        # =================================================================
        partner, created = Partner.objects.get_or_create(
            code='DEMO001',
            defaults={
                'name': 'Demo Company',
                'contact_email': 'demo@example.com',
                'contact_phone': '+1234567890',
                'address': '123 Demo Street, Demo City',
                'is_active': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created partner: {partner.name}'))
        else:
            self.stdout.write(f'Partner already exists: {partner.name}')

        # =================================================================
        # Create Stores
        # =================================================================
        stores_data = [
            {
                'name': 'Main Store',
                'code': 'MAIN',
                'address': '123 Main Street',
                'phone': '+1234567890',
                'is_active': True,
                'is_default': True,
            },
            {
                'name': 'Branch Store',
                'code': 'BRANCH',
                'address': '456 Branch Avenue',
                'phone': '+0987654321',
                'is_active': True,
                'is_default': False,
            },
        ]

        stores = []
        for store_data in stores_data:
            store, created = Store.objects.get_or_create(
                partner=partner,
                code=store_data['code'],
                defaults=store_data
            )
            stores.append(store)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created store: {store.name}'))
            else:
                self.stdout.write(f'Store already exists: {store.name}')

        # =================================================================
        # Create Product Categories
        # =================================================================
        categories_data = [
            {'name': 'Beverages', 'description': 'Drinks and beverages'},
            {'name': 'Snacks', 'description': 'Chips, crackers, and snacks'},
            {'name': 'Dairy', 'description': 'Milk, cheese, and dairy products'},
            {'name': 'Groceries', 'description': 'General grocery items'},
            {'name': 'Personal Care', 'description': 'Personal care and hygiene products'},
        ]

        categories = []
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                partner=partner,
                name=cat_data['name'],
                defaults={'description': cat_data['description']}
            )
            categories.append(category)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created category: {category.name}'))

        # =================================================================
        # Create Supplier
        # =================================================================
        supplier, created = Supplier.objects.get_or_create(
            partner=partner,
            name='Demo Supplier',
            defaults={
                'contact_person': 'John Doe',
                'email': 'supplier@demo.com',
                'phone': '+1122334455',
                'address': '789 Supplier Road',
                'is_active': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created supplier: {supplier.name}'))

        # =================================================================
        # Create Products
        # =================================================================
        products_data = [
            # Beverages
            {'name': 'Coca-Cola 500ml', 'sku': 'BEV001', 'barcode': '4901234567890', 'category': 'Beverages', 'cost_price': Decimal('25.00'), 'selling_price': Decimal('35.00'), 'stock': 100},
            {'name': 'Pepsi 500ml', 'sku': 'BEV002', 'barcode': '4901234567891', 'category': 'Beverages', 'cost_price': Decimal('24.00'), 'selling_price': Decimal('34.00'), 'stock': 80},
            # Snacks
            {'name': 'Potato Chips Original', 'sku': 'SNK001', 'barcode': '4901234567892', 'category': 'Snacks', 'cost_price': Decimal('30.00'), 'selling_price': Decimal('45.00'), 'stock': 50},
            {'name': 'Cheese Crackers', 'sku': 'SNK002', 'barcode': '4901234567893', 'category': 'Snacks', 'cost_price': Decimal('20.00'), 'selling_price': Decimal('30.00'), 'stock': 60},
            # Dairy
            {'name': 'Fresh Milk 1L', 'sku': 'DRY001', 'barcode': '4901234567894', 'category': 'Dairy', 'cost_price': Decimal('55.00'), 'selling_price': Decimal('75.00'), 'stock': 30},
            {'name': 'Cheddar Cheese 200g', 'sku': 'DRY002', 'barcode': '4901234567895', 'category': 'Dairy', 'cost_price': Decimal('80.00'), 'selling_price': Decimal('120.00'), 'stock': 25},
            # Groceries
            {'name': 'White Rice 1kg', 'sku': 'GRC001', 'barcode': '4901234567896', 'category': 'Groceries', 'cost_price': Decimal('45.00'), 'selling_price': Decimal('60.00'), 'stock': 40},
            {'name': 'Instant Noodles', 'sku': 'GRC002', 'barcode': '4901234567897', 'category': 'Groceries', 'cost_price': Decimal('12.00'), 'selling_price': Decimal('18.00'), 'stock': 100},
            # Personal Care
            {'name': 'Shampoo 200ml', 'sku': 'PRC001', 'barcode': '4901234567898', 'category': 'Personal Care', 'cost_price': Decimal('65.00'), 'selling_price': Decimal('95.00'), 'stock': 35},
            {'name': 'Toothpaste 100g', 'sku': 'PRC002', 'barcode': '4901234567899', 'category': 'Personal Care', 'cost_price': Decimal('35.00'), 'selling_price': Decimal('50.00'), 'stock': 45},
        ]

        category_map = {cat.name: cat for cat in categories}

        for prod_data in products_data:
            category = category_map[prod_data['category']]
            product, created = Product.objects.get_or_create(
                partner=partner,
                sku=prod_data['sku'],
                defaults={
                    'name': prod_data['name'],
                    'barcode': prod_data['barcode'],
                    'category': category,
                    'cost_price': prod_data['cost_price'],
                    'selling_price': prod_data['selling_price'],
                    'wholesale_price': prod_data['selling_price'] * Decimal('0.9'),
                    'is_active': True,
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created product: {product.name}'))
                
                # Create store inventory for each store
                for store in stores:
                    StoreInventory.objects.get_or_create(
                        product=product,
                        store=store,
                        defaults={
                            'current_stock': prod_data['stock'],
                            'minimum_stock_level': 10,
                        }
                    )
                
                # Add product to available stores
                product.available_stores.set(stores)

        # =================================================================
        # Create Expense Categories
        # =================================================================
        expense_categories_data = [
            {'name': 'Utilities', 'description': 'Electricity, water, internet', 'color': '#3B82F6'},
            {'name': 'Supplies', 'description': 'Office and store supplies', 'color': '#10B981'},
            {'name': 'Rent', 'description': 'Store rent and lease', 'color': '#F59E0B'},
        ]

        for exp_cat_data in expense_categories_data:
            exp_cat, created = ExpenseCategory.objects.get_or_create(
                partner=partner,
                name=exp_cat_data['name'],
                defaults={
                    'description': exp_cat_data['description'],
                    'color': exp_cat_data['color'],
                    'is_active': True,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created expense category: {exp_cat.name}'))

        # =================================================================
        # Summary
        # =================================================================
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('Demo data loaded successfully!'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(f'Partner: {partner.name}')
        self.stdout.write(f'Stores: {Store.objects.filter(partner=partner).count()}')
        self.stdout.write(f'Categories: {Category.objects.filter(partner=partner).count()}')
        self.stdout.write(f'Products: {Product.objects.filter(partner=partner).count()}')
        self.stdout.write(f'Suppliers: {Supplier.objects.filter(partner=partner).count()}')
        self.stdout.write(f'Expense Categories: {ExpenseCategory.objects.filter(partner=partner).count()}')
