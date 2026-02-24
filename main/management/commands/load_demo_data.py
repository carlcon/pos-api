"""
Django management command to load demo data for POS application.
Creates initial partner, stores, categories, products, and other demo data.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
import random


class Command(BaseCommand):
    help = 'Load demo data for POS application (partner, stores, products, etc.)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before loading demo data',
        )
        parser.add_argument(
            '--username',
            type=str,
            default='demo',
            help='Demo user username (default: demo)',
        )
        parser.add_argument(
            '--password',
            type=str,
            default='Demo1234@',
            help='Demo user password (default: Demo1234@)',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        from users.models import Partner, User
        from stores.models import Store
        from inventory.models import Category, Product, Supplier, StoreInventory
        from expenses.models import ExpenseCategory, Expense
        from sales.models import Sale, SaleItem
        from stock.models import StockTransaction

        username = options['username']
        password = options['password']

        self.stdout.write(self.style.NOTICE('Loading demo data...'))

        # =================================================================
        # Create Demo Partner
        # =================================================================
        partner, created = Partner.objects.get_or_create(
            code='DEMO001',
            defaults={
                'name': 'JCC Motor Parts & Supplies',
                'contact_email': 'info@jccinventory.com',
                'contact_phone': '+63 912 345 6789',
                'address': '123 Main Street, Makati City, Metro Manila',
                'is_active': True,
                'barcode_format': 'EAN13',
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created partner: {partner.name}'))
        else:
            self.stdout.write(f'Partner already exists: {partner.name}')

        # =================================================================
        # Create Demo User
        # =================================================================
        demo_user, user_created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': f'{username}@jccinventory.com',
                'first_name': 'Demo',
                'last_name': 'User',
                'role': 'ADMIN',
                'partner': partner,
                'is_active': True,
                'is_staff': True,
            }
        )
        if user_created:
            demo_user.set_password(password)
            demo_user.save()
            self.stdout.write(self.style.SUCCESS(f'Created demo user: {username} / {password}'))
        else:
            # Update password if user exists
            demo_user.set_password(password)
            demo_user.partner = partner
            demo_user.save()
            self.stdout.write(f'Demo user already exists, password updated: {username}')

        # =================================================================
        # Create Stores
        # =================================================================
        stores_data = [
            {
                'name': 'Main Store - Makati',
                'code': 'MAIN',
                'address': '123 Main Street, Makati City',
                'contact_phone': '+63 912 345 6789',
                'is_active': True,
                'is_default': True,
            },
            {
                'name': 'Branch - Quezon City',
                'code': 'QC01',
                'address': '456 Commonwealth Ave, Quezon City',
                'contact_phone': '+63 912 987 6543',
                'is_active': True,
                'is_default': False,
            },
            {
                'name': 'Branch - Cebu',
                'code': 'CEB01',
                'address': '789 Osmena Blvd, Cebu City',
                'contact_phone': '+63 912 555 1234',
                'is_active': True,
                'is_default': False,
            },
        ]

        stores = []
        for store_data in stores_data:
            store, created = Store.objects.get_or_create(
                partner=partner,
                code=store_data['code'],
                defaults={
                    'name': store_data['name'],
                    'address': store_data['address'],
                    'contact_phone': store_data['contact_phone'],
                    'is_active': store_data['is_active'],
                    'is_default': store_data['is_default'],
                }
            )
            stores.append(store)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created store: {store.name}'))
            else:
                self.stdout.write(f'Store already exists: {store.name}')

        # =================================================================
        # Create Product Categories (Motor Parts)
        # =================================================================
        categories_data = [
            {'name': 'Engine Parts', 'description': 'Engine components and accessories'},
            {'name': 'Brake System', 'description': 'Brake pads, rotors, calipers, brake fluid'},
            {'name': 'Electrical System', 'description': 'Batteries, alternators, starters, wiring'},
            {'name': 'Suspension', 'description': 'Shock absorbers, springs, control arms'},
            {'name': 'Filters', 'description': 'Oil filters, air filters, fuel filters'},
            {'name': 'Oils & Fluids', 'description': 'Engine oil, transmission fluid, coolant'},
            {'name': 'Belts & Hoses', 'description': 'Drive belts, timing belts, radiator hoses'},
            {'name': 'Lighting', 'description': 'Headlights, tail lights, bulbs'},
            {'name': 'Tires & Wheels', 'description': 'Tires, rims, wheel accessories'},
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
        # Create Suppliers
        # =================================================================
        suppliers_data = [
            {'name': 'Toyota Genuine Parts', 'contact_person': 'Juan Cruz', 'email': 'supplier@toyota.ph', 'phone': '+63 2 8888 1234', 'address': 'Bonifacio Global City, Taguig'},
            {'name': 'Denso Philippines', 'contact_person': 'Maria Santos', 'email': 'orders@denso.ph', 'phone': '+63 2 8888 5678', 'address': 'Laguna Technopark, Sta. Rosa'},
            {'name': 'Brembo Asia Pacific', 'contact_person': 'Robert Lim', 'email': 'sales@brembo.asia', 'phone': '+63 2 8888 9012', 'address': 'Cavite Economic Zone'},
        ]
        
        suppliers = []
        for sup_data in suppliers_data:
            supplier, created = Supplier.objects.get_or_create(
                partner=partner,
                name=sup_data['name'],
                defaults={
                    'contact_person': sup_data['contact_person'],
                    'email': sup_data['email'],
                    'phone': sup_data['phone'],
                    'address': sup_data['address'],
                    'is_active': True,
                }
            )
            suppliers.append(supplier)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created supplier: {supplier.name}'))

        # =================================================================
        # Create Products (Motor Parts Inventory)
        # =================================================================
        products_data = [
            # Engine Parts
            {'name': 'Oil Filter - Toyota Vios', 'sku': 'ENG-001', 'barcode': '6901234567001', 'category': 'Engine Parts', 'cost_price': Decimal('180.00'), 'selling_price': Decimal('350.00'), 'stock': 150, 'brand': 'Toyota', 'model': 'Vios 2015-2023'},
            {'name': 'Spark Plug Set (4pcs) - NGK', 'sku': 'ENG-002', 'barcode': '6901234567002', 'category': 'Engine Parts', 'cost_price': Decimal('650.00'), 'selling_price': Decimal('1200.00'), 'stock': 80, 'brand': 'NGK', 'model': 'Universal'},
            {'name': 'Timing Belt Kit - Honda', 'sku': 'ENG-003', 'barcode': '6901234567003', 'category': 'Engine Parts', 'cost_price': Decimal('2800.00'), 'selling_price': Decimal('4500.00'), 'stock': 25, 'brand': 'Gates', 'model': 'Honda Civic'},
            {'name': 'Engine Gasket Set', 'sku': 'ENG-004', 'barcode': '6901234567004', 'category': 'Engine Parts', 'cost_price': Decimal('1500.00'), 'selling_price': Decimal('2800.00'), 'stock': 35, 'brand': 'Fel-Pro', 'model': 'Ford Ranger'},
            
            # Brake System
            {'name': 'Front Brake Pads - Brembo', 'sku': 'BRK-001', 'barcode': '6901234567101', 'category': 'Brake System', 'cost_price': Decimal('1200.00'), 'selling_price': Decimal('2200.00'), 'stock': 95, 'brand': 'Brembo', 'model': 'Toyota Innova'},
            {'name': 'Rear Brake Pads - Brembo', 'sku': 'BRK-002', 'barcode': '6901234567102', 'category': 'Brake System', 'cost_price': Decimal('1000.00'), 'selling_price': Decimal('1800.00'), 'stock': 85, 'brand': 'Brembo', 'model': 'Toyota Innova'},
            {'name': 'Brake Rotor Front', 'sku': 'BRK-003', 'barcode': '6901234567103', 'category': 'Brake System', 'cost_price': Decimal('1800.00'), 'selling_price': Decimal('3200.00'), 'stock': 55, 'brand': 'ACDelco', 'model': 'Honda Civic'},
            {'name': 'Brake Fluid DOT 4 (1L)', 'sku': 'BRK-004', 'barcode': '6901234567104', 'category': 'Brake System', 'cost_price': Decimal('280.00'), 'selling_price': Decimal('450.00'), 'stock': 120, 'brand': 'Castrol', 'model': 'Universal'},
            
            # Electrical System
            {'name': 'Car Battery 12V 70AH', 'sku': 'ELC-001', 'barcode': '6901234567201', 'category': 'Electrical System', 'cost_price': Decimal('4500.00'), 'selling_price': Decimal('6500.00'), 'stock': 45, 'brand': 'Motolite', 'model': 'Universal'},
            {'name': 'Alternator Assembly - Toyota', 'sku': 'ELC-002', 'barcode': '6901234567202', 'category': 'Electrical System', 'cost_price': Decimal('8500.00'), 'selling_price': Decimal('12000.00'), 'stock': 18, 'brand': 'Denso', 'model': 'Toyota Fortuner'},
            {'name': 'Starter Motor - Honda', 'sku': 'ELC-003', 'barcode': '6901234567203', 'category': 'Electrical System', 'cost_price': Decimal('5500.00'), 'selling_price': Decimal('8500.00'), 'stock': 22, 'brand': 'Bosch', 'model': 'Honda Accord'},
            {'name': 'Ignition Coil Set', 'sku': 'ELC-004', 'barcode': '6901234567204', 'category': 'Electrical System', 'cost_price': Decimal('2800.00'), 'selling_price': Decimal('4500.00'), 'stock': 30, 'brand': 'Delphi', 'model': 'Nissan Navara'},
            
            # Suspension
            {'name': 'Front Shock Absorber', 'sku': 'SUS-001', 'barcode': '6901234567301', 'category': 'Suspension', 'cost_price': Decimal('2200.00'), 'selling_price': Decimal('3800.00'), 'stock': 40, 'brand': 'KYB', 'model': 'Mitsubishi Montero'},
            {'name': 'Rear Shock Absorber', 'sku': 'SUS-002', 'barcode': '6901234567302', 'category': 'Suspension', 'cost_price': Decimal('2000.00'), 'selling_price': Decimal('3500.00'), 'stock': 38, 'brand': 'KYB', 'model': 'Mitsubishi Montero'},
            {'name': 'Coil Spring Front (Pair)', 'sku': 'SUS-003', 'barcode': '6901234567303', 'category': 'Suspension', 'cost_price': Decimal('3200.00'), 'selling_price': Decimal('5200.00'), 'stock': 32, 'brand': 'Moog', 'model': 'Toyota Hilux'},
            
            # Filters
            {'name': 'Air Filter - Toyota Vios', 'sku': 'FLT-001', 'barcode': '6901234567401', 'category': 'Filters', 'cost_price': Decimal('350.00'), 'selling_price': Decimal('650.00'), 'stock': 100, 'brand': 'Toyota', 'model': 'Vios 2015-2023'},
            {'name': 'Cabin Filter - Honda', 'sku': 'FLT-002', 'barcode': '6901234567402', 'category': 'Filters', 'cost_price': Decimal('450.00'), 'selling_price': Decimal('850.00'), 'stock': 75, 'brand': 'Honda', 'model': 'City/Jazz'},
            {'name': 'Fuel Filter - Universal', 'sku': 'FLT-003', 'barcode': '6901234567403', 'category': 'Filters', 'cost_price': Decimal('280.00'), 'selling_price': Decimal('500.00'), 'stock': 90, 'brand': 'Bosch', 'model': 'Universal'},
            
            # Oils & Fluids
            {'name': 'Engine Oil 10W-40 (4L)', 'sku': 'OIL-001', 'barcode': '6901234567501', 'category': 'Oils & Fluids', 'cost_price': Decimal('1200.00'), 'selling_price': Decimal('1800.00'), 'stock': 200, 'brand': 'Castrol', 'model': 'Universal'},
            {'name': 'Engine Oil 5W-30 Fully Synthetic (4L)', 'sku': 'OIL-002', 'barcode': '6901234567502', 'category': 'Oils & Fluids', 'cost_price': Decimal('2200.00'), 'selling_price': Decimal('3200.00'), 'stock': 150, 'brand': 'Mobil 1', 'model': 'Universal'},
            {'name': 'Transmission Fluid ATF (1L)', 'sku': 'OIL-003', 'barcode': '6901234567503', 'category': 'Oils & Fluids', 'cost_price': Decimal('450.00'), 'selling_price': Decimal('750.00'), 'stock': 80, 'brand': 'Aisin', 'model': 'Universal'},
            {'name': 'Coolant Pre-Mixed (4L)', 'sku': 'OIL-004', 'barcode': '6901234567504', 'category': 'Oils & Fluids', 'cost_price': Decimal('380.00'), 'selling_price': Decimal('650.00'), 'stock': 100, 'brand': 'Prestone', 'model': 'Universal'},
            
            # Belts & Hoses
            {'name': 'Drive Belt V-Ribbed', 'sku': 'BLT-001', 'barcode': '6901234567601', 'category': 'Belts & Hoses', 'cost_price': Decimal('650.00'), 'selling_price': Decimal('1100.00'), 'stock': 60, 'brand': 'Gates', 'model': 'Toyota Innova'},
            {'name': 'Radiator Hose Upper', 'sku': 'BLT-002', 'barcode': '6901234567602', 'category': 'Belts & Hoses', 'cost_price': Decimal('380.00'), 'selling_price': Decimal('650.00'), 'stock': 45, 'brand': 'Continental', 'model': 'Honda Civic'},
            
            # Lighting
            {'name': 'Headlight Bulb H4 (Pair)', 'sku': 'LGT-001', 'barcode': '6901234567701', 'category': 'Lighting', 'cost_price': Decimal('450.00'), 'selling_price': Decimal('850.00'), 'stock': 80, 'brand': 'Philips', 'model': 'Universal'},
            {'name': 'LED Headlight Kit H11', 'sku': 'LGT-002', 'barcode': '6901234567702', 'category': 'Lighting', 'cost_price': Decimal('1800.00'), 'selling_price': Decimal('3200.00'), 'stock': 35, 'brand': 'Osram', 'model': 'Universal'},
            {'name': 'Tail Light Assembly Left', 'sku': 'LGT-003', 'barcode': '6901234567703', 'category': 'Lighting', 'cost_price': Decimal('2500.00'), 'selling_price': Decimal('4200.00'), 'stock': 20, 'brand': 'Depo', 'model': 'Toyota Vios'},
            
            # Tires & Wheels
            {'name': 'Tire 205/65R15 - Bridgestone', 'sku': 'TIR-001', 'barcode': '6901234567801', 'category': 'Tires & Wheels', 'cost_price': Decimal('3500.00'), 'selling_price': Decimal('5200.00'), 'stock': 40, 'brand': 'Bridgestone', 'model': 'SUV/Sedan'},
            {'name': 'Tire 265/70R16 - Dunlop', 'sku': 'TIR-002', 'barcode': '6901234567802', 'category': 'Tires & Wheels', 'cost_price': Decimal('5500.00'), 'selling_price': Decimal('7800.00'), 'stock': 24, 'brand': 'Dunlop', 'model': 'SUV/Pickup'},
        ]

        category_map = {cat.name: cat for cat in categories}
        created_products = []

        for prod_data in products_data:
            category = category_map[prod_data['category']]
            product, created = Product.objects.get_or_create(
                partner=partner,
                sku=prod_data['sku'],
                defaults={
                    'name': prod_data['name'],
                    'barcode': prod_data['barcode'],
                    'category': category,
                    'brand': prod_data.get('brand', ''),
                    'model_compatibility': prod_data.get('model', ''),
                    'cost_price': prod_data['cost_price'],
                    'selling_price': prod_data['selling_price'],
                    'wholesale_price': prod_data['selling_price'] * Decimal('0.85'),
                    'is_active': True,
                }
            )
            created_products.append(product)
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created product: {product.name}'))
                
                # Create store inventory for each store
                for store in stores:
                    StoreInventory.objects.get_or_create(
                        product=product,
                        store=store,
                        defaults={
                            'current_stock': prod_data['stock'],
                            'minimum_stock_level': max(5, prod_data['stock'] // 10),
                        }
                    )
                
                # Add product to available stores
                product.available_stores.set(stores)

        # =================================================================
        # Create Expense Categories
        # =================================================================
        expense_categories_data = [
            {'name': 'Utilities', 'description': 'Electricity, water, internet', 'color': '#3B82F6'},
            {'name': 'Store Supplies', 'description': 'Office and store supplies', 'color': '#10B981'},
            {'name': 'Rent', 'description': 'Store rent and lease', 'color': '#F59E0B'},
            {'name': 'Salaries', 'description': 'Employee salaries and wages', 'color': '#8B5CF6'},
            {'name': 'Transportation', 'description': 'Delivery and transport costs', 'color': '#EC4899'},
            {'name': 'Maintenance', 'description': 'Equipment and store maintenance', 'color': '#06B6D4'},
        ]

        expense_cats = {}
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
            expense_cats[exp_cat_data['name']] = exp_cat
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created expense category: {exp_cat.name}'))

        # =================================================================
        # Create Sample Sales (Last 30 days)
        # =================================================================
        self.stdout.write(self.style.NOTICE('Creating sample sales...'))
        
        # Get products for sales
        products = list(Product.objects.filter(partner=partner)[:20])
        main_store = stores[0]
        
        # Create sales for the past 30 days
        sales_created = 0
        for days_ago in range(30):
            sale_date = timezone.now() - timedelta(days=days_ago)
            # Create 3-8 sales per day
            num_sales = random.randint(3, 8)
            
            for sale_num in range(num_sales):
                sale_number = f"SALE-{sale_date.strftime('%Y%m%d')}-{sale_num+1:03d}"
                
                # Check if sale already exists
                if Sale.objects.filter(partner=partner, sale_number=sale_number).exists():
                    continue
                
                # Random payment method
                payment_methods = ['CASH', 'CASH', 'CASH', 'CARD', 'BANK_TRANSFER']  # Cash is more common
                payment_method = random.choice(payment_methods)
                
                # Create sale
                sale = Sale.objects.create(
                    partner=partner,
                    store=main_store,
                    sale_number=sale_number,
                    customer_name=random.choice([None, 'Walk-in Customer', 'Juan dela Cruz', 'Maria Santos', 'Pedro Garcia']),
                    payment_method=payment_method,
                    subtotal=Decimal('0.00'),
                    discount=Decimal('0.00'),
                    total_amount=Decimal('0.00'),
                    cashier=demo_user,
                )
                # Override created_at
                Sale.objects.filter(pk=sale.pk).update(created_at=sale_date)
                
                # Add 1-5 items to sale
                num_items = random.randint(1, 5)
                sale_products = random.sample(products, min(num_items, len(products)))
                
                subtotal = Decimal('0.00')
                for product in sale_products:
                    quantity = random.randint(1, 3)
                    unit_price = product.selling_price
                    line_total = unit_price * quantity
                    
                    SaleItem.objects.create(
                        sale=sale,
                        product=product,
                        quantity=quantity,
                        unit_price=unit_price,
                        discount=Decimal('0.00'),
                        line_total=line_total,
                    )
                    subtotal += line_total
                
                # Apply occasional discount
                discount = Decimal('0.00')
                if random.random() < 0.2:  # 20% chance of discount
                    discount = (subtotal * Decimal('0.05')).quantize(Decimal('0.01'))
                
                sale.subtotal = subtotal
                sale.discount = discount
                sale.total_amount = subtotal - discount
                sale.save()
                sales_created += 1
        
        self.stdout.write(self.style.SUCCESS(f'Created {sales_created} sample sales'))

        # =================================================================
        # Create Sample Expenses (Last 30 days)
        # =================================================================
        self.stdout.write(self.style.NOTICE('Creating sample expenses...'))
        
        expenses_data = [
            # Monthly expenses (added at start of data)
            {'title': 'Store Rent - February 2026', 'category': 'Rent', 'amount': Decimal('45000.00'), 'days_ago': 25},
            {'title': 'Electricity Bill - January', 'category': 'Utilities', 'amount': Decimal('12500.00'), 'days_ago': 20},
            {'title': 'Internet Service', 'category': 'Utilities', 'amount': Decimal('2500.00'), 'days_ago': 15},
            {'title': 'Water Bill', 'category': 'Utilities', 'amount': Decimal('1800.00'), 'days_ago': 18},
            {'title': 'Office Supplies', 'category': 'Store Supplies', 'amount': Decimal('3500.00'), 'days_ago': 10},
            {'title': 'Printer Paper and Ink', 'category': 'Store Supplies', 'amount': Decimal('2200.00'), 'days_ago': 8},
            {'title': 'Staff Salary - Week 1', 'category': 'Salaries', 'amount': Decimal('25000.00'), 'days_ago': 28},
            {'title': 'Staff Salary - Week 2', 'category': 'Salaries', 'amount': Decimal('25000.00'), 'days_ago': 21},
            {'title': 'Staff Salary - Week 3', 'category': 'Salaries', 'amount': Decimal('25000.00'), 'days_ago': 14},
            {'title': 'Staff Salary - Week 4', 'category': 'Salaries', 'amount': Decimal('25000.00'), 'days_ago': 7},
            {'title': 'Delivery Van Fuel', 'category': 'Transportation', 'amount': Decimal('5500.00'), 'days_ago': 5},
            {'title': 'AC Unit Repair', 'category': 'Maintenance', 'amount': Decimal('3800.00'), 'days_ago': 12},
            {'title': 'POS Terminal Maintenance', 'category': 'Maintenance', 'amount': Decimal('1500.00'), 'days_ago': 3},
        ]
        
        expenses_created = 0
        for exp_data in expenses_data:
            expense_date = timezone.now() - timedelta(days=exp_data['days_ago'])
            
            if not Expense.objects.filter(partner=partner, title=exp_data['title']).exists():
                Expense.objects.create(
                    partner=partner,
                    store=main_store,
                    title=exp_data['title'],
                    amount=exp_data['amount'],
                    category=expense_cats[exp_data['category']],
                    payment_method='CASH' if exp_data['amount'] < Decimal('10000') else 'BANK_TRANSFER',
                    expense_date=expense_date.date(),
                    created_by=demo_user,
                )
                expenses_created += 1
        
        self.stdout.write(self.style.SUCCESS(f'Created {expenses_created} sample expenses'))

        # =================================================================
        # Create Stock Transactions (Recent stock-in records)
        # =================================================================
        self.stdout.write(self.style.NOTICE('Creating sample stock transactions...'))
        
        stock_tx_created = 0
        for product in products[:10]:  # First 10 products
            # Get store inventory
            for store in stores[:1]:  # Main store only
                try:
                    inventory = StoreInventory.objects.get(product=product, store=store)
                    
                    # Create a stock-in transaction from 15 days ago
                    if not StockTransaction.objects.filter(
                        partner=partner, 
                        product=product, 
                        reason='PURCHASE'
                    ).exists():
                        quantity_in = random.randint(20, 50)
                        StockTransaction.objects.create(
                            partner=partner,
                            store=store,
                            product=product,
                            transaction_type='IN',
                            reason='PURCHASE',
                            quantity=quantity_in,
                            quantity_before=inventory.current_stock - quantity_in,
                            quantity_after=inventory.current_stock,
                            unit_cost=product.cost_price,
                            total_cost=product.cost_price * quantity_in,
                            reference_number=f"PO-{timezone.now().strftime('%Y%m')}-{random.randint(100, 999)}",
                            notes='Initial stock purchase',
                            performed_by=demo_user,
                        )
                        stock_tx_created += 1
                except StoreInventory.DoesNotExist:
                    pass
        
        self.stdout.write(self.style.SUCCESS(f'Created {stock_tx_created} stock transactions'))

        # =================================================================
        # Assign demo user to stores
        # =================================================================
        demo_user.assigned_stores.set(stores)
        self.stdout.write(self.style.SUCCESS(f'Assigned demo user to {len(stores)} stores'))

        # =================================================================
        # Summary
        # =================================================================
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('   DEMO DATA LOADED SUCCESSFULLY!'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')
        self.stdout.write(f'  Partner: {partner.name}')
        self.stdout.write(f'  Demo User: {username} / {password}')
        self.stdout.write('')
        self.stdout.write(f'  Stores: {Store.objects.filter(partner=partner).count()}')
        self.stdout.write(f'  Categories: {Category.objects.filter(partner=partner).count()}')
        self.stdout.write(f'  Products: {Product.objects.filter(partner=partner).count()}')
        self.stdout.write(f'  Suppliers: {Supplier.objects.filter(partner=partner).count()}')
        self.stdout.write(f'  Sales: {Sale.objects.filter(partner=partner).count()}')
        self.stdout.write(f'  Expenses: {Expense.objects.filter(partner=partner).count()}')
        self.stdout.write(f'  Stock Transactions: {StockTransaction.objects.filter(partner=partner).count()}')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.WARNING(f'  Login at: https://api.jccinventory.com/admin/'))
        self.stdout.write(self.style.WARNING(f'  Username: {username}'))
        self.stdout.write(self.style.WARNING(f'  Password: {password}'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
