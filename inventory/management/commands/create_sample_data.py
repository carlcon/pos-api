from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from inventory.models import Category, Product, Supplier, PurchaseOrder, POItem
from decimal import Decimal
from datetime import date, timedelta

User = get_user_model()


class Command(BaseCommand):
    help = 'Create sample data for motor parts inventory'

    def handle(self, *args, **kwargs):
        self.stdout.write('Creating sample data...')

        # Get or create admin user
        admin_user, _ = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if _:
            admin_user.set_password('admin123')
            admin_user.save()

        # Create Categories
        categories_data = [
            {'name': 'Engine Parts', 'description': 'Engine components and accessories'},
            {'name': 'Electrical System', 'description': 'Batteries, alternators, starters, wiring'},
            {'name': 'Brake System', 'description': 'Brake pads, rotors, calipers, brake fluid'},
            {'name': 'Suspension', 'description': 'Shock absorbers, springs, control arms'},
            {'name': 'Transmission', 'description': 'Transmission parts and fluids'},
            {'name': 'Cooling System', 'description': 'Radiators, water pumps, thermostats'},
            {'name': 'Exhaust System', 'description': 'Mufflers, catalytic converters, pipes'},
            {'name': 'Filters', 'description': 'Oil filters, air filters, fuel filters'},
            {'name': 'Belts & Hoses', 'description': 'Drive belts, timing belts, radiator hoses'},
            {'name': 'Lighting', 'description': 'Headlights, tail lights, bulbs'},
            {'name': 'Body Parts', 'description': 'Bumpers, fenders, mirrors'},
            {'name': 'Interior', 'description': 'Seat covers, floor mats, dashboard accessories'},
            {'name': 'Oils & Fluids', 'description': 'Engine oil, transmission fluid, coolant'},
            {'name': 'Tires & Wheels', 'description': 'Tires, rims, wheel accessories'},
        ]

        categories = {}
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={'description': cat_data['description']}
            )
            categories[cat_data['name']] = category
            if created:
                self.stdout.write(f'  Created category: {category.name}')

        # Create Products
        products_data = [
            # Engine Parts
            {'sku': 'ENG-001', 'name': 'Oil Filter Toyota', 'category': 'Engine Parts', 'barcode': '1234567890001', 
             'cost': '5.50', 'price': '12.99', 'stock': 150, 'min_stock': 30, 'brand': 'Toyota', 'model': 'Camry, Corolla'},
            {'sku': 'ENG-002', 'name': 'Spark Plug Set (4pcs)', 'category': 'Engine Parts', 'barcode': '1234567890002',
             'cost': '18.00', 'price': '35.99', 'stock': 80, 'min_stock': 20, 'brand': 'NGK', 'model': 'Universal'},
            {'sku': 'ENG-003', 'name': 'Timing Belt Kit', 'category': 'Engine Parts', 'barcode': '1234567890003',
             'cost': '85.00', 'price': '165.00', 'stock': 25, 'min_stock': 10, 'brand': 'Gates', 'model': 'Honda Civic'},
            {'sku': 'ENG-004', 'name': 'Engine Gasket Set', 'category': 'Engine Parts', 'barcode': '1234567890004',
             'cost': '45.00', 'price': '89.99', 'stock': 35, 'min_stock': 10, 'brand': 'Fel-Pro', 'model': 'Ford F-150'},
            {'sku': 'ENG-005', 'name': 'Piston Ring Set', 'category': 'Engine Parts', 'barcode': '1234567890005',
             'cost': '120.00', 'price': '225.00', 'stock': 12, 'min_stock': 5, 'brand': 'Mahle', 'model': 'BMW 3 Series'},

            # Electrical System
            {'sku': 'ELC-001', 'name': 'Car Battery 12V 70AH', 'category': 'Electrical System', 'barcode': '1234567890101',
             'cost': '65.00', 'price': '129.99', 'stock': 45, 'min_stock': 15, 'brand': 'Optima', 'model': 'Universal'},
            {'sku': 'ELC-002', 'name': 'Alternator Toyota', 'category': 'Electrical System', 'barcode': '1234567890102',
             'cost': '145.00', 'price': '289.99', 'stock': 18, 'min_stock': 8, 'brand': 'Denso', 'model': 'Camry 2015-2020'},
            {'sku': 'ELC-003', 'name': 'Starter Motor Honda', 'category': 'Electrical System', 'barcode': '1234567890103',
             'cost': '95.00', 'price': '185.00', 'stock': 22, 'min_stock': 10, 'brand': 'Bosch', 'model': 'Accord 2013-2018'},
            {'sku': 'ELC-004', 'name': 'Ignition Coil Set', 'category': 'Electrical System', 'barcode': '1234567890104',
             'cost': '75.00', 'price': '149.99', 'stock': 30, 'min_stock': 12, 'brand': 'Delphi', 'model': 'Nissan Altima'},

            # Brake System
            {'sku': 'BRK-001', 'name': 'Front Brake Pads', 'category': 'Brake System', 'barcode': '1234567890201',
             'cost': '28.00', 'price': '55.99', 'stock': 95, 'min_stock': 25, 'brand': 'Brembo', 'model': 'Toyota Camry'},
            {'sku': 'BRK-002', 'name': 'Rear Brake Pads', 'category': 'Brake System', 'barcode': '1234567890202',
             'cost': '25.00', 'price': '49.99', 'stock': 85, 'min_stock': 25, 'brand': 'Brembo', 'model': 'Toyota Camry'},
            {'sku': 'BRK-003', 'name': 'Brake Rotor Front', 'category': 'Brake System', 'barcode': '1234567890203',
             'cost': '42.00', 'price': '82.99', 'stock': 55, 'min_stock': 20, 'brand': 'ACDelco', 'model': 'Honda Civic'},
            {'sku': 'BRK-004', 'name': 'Brake Fluid DOT 4 (1L)', 'category': 'Brake System', 'barcode': '1234567890204',
             'cost': '6.50', 'price': '14.99', 'stock': 120, 'min_stock': 30, 'brand': 'Castrol', 'model': 'Universal', 'uom': 'LITER'},
            {'sku': 'BRK-005', 'name': 'Brake Caliper Assembly', 'category': 'Brake System', 'barcode': '1234567890205',
             'cost': '68.00', 'price': '135.00', 'stock': 24, 'min_stock': 8, 'brand': 'Cardone', 'model': 'Ford F-150'},

            # Suspension
            {'sku': 'SUS-001', 'name': 'Front Shock Absorber', 'category': 'Suspension', 'barcode': '1234567890301',
             'cost': '55.00', 'price': '109.99', 'stock': 40, 'min_stock': 15, 'brand': 'KYB', 'model': 'Honda Accord'},
            {'sku': 'SUS-002', 'name': 'Rear Shock Absorber', 'category': 'Suspension', 'barcode': '1234567890302',
             'cost': '52.00', 'price': '104.99', 'stock': 38, 'min_stock': 15, 'brand': 'KYB', 'model': 'Honda Accord'},
            {'sku': 'SUS-003', 'name': 'Coil Spring Front', 'category': 'Suspension', 'barcode': '1234567890303',
             'cost': '38.00', 'price': '75.99', 'stock': 32, 'min_stock': 12, 'brand': 'Moog', 'model': 'Toyota Camry'},
            {'sku': 'SUS-004', 'name': 'Control Arm Lower', 'category': 'Suspension', 'barcode': '1234567890304',
             'cost': '72.00', 'price': '145.00', 'stock': 28, 'min_stock': 10, 'brand': 'TRW', 'model': 'BMW 3 Series'},

            # Filters
            {'sku': 'FLT-001', 'name': 'Air Filter Honda', 'category': 'Filters', 'barcode': '1234567890401',
             'cost': '8.50', 'price': '18.99', 'stock': 110, 'min_stock': 30, 'brand': 'K&N', 'model': 'Civic, Accord'},
            {'sku': 'FLT-002', 'name': 'Cabin Air Filter', 'category': 'Filters', 'barcode': '1234567890402',
             'cost': '7.00', 'price': '15.99', 'stock': 95, 'min_stock': 25, 'brand': 'Mann Filter', 'model': 'Universal'},
            {'sku': 'FLT-003', 'name': 'Fuel Filter Toyota', 'category': 'Filters', 'barcode': '1234567890403',
             'cost': '12.00', 'price': '25.99', 'stock': 75, 'min_stock': 20, 'brand': 'Wix', 'model': 'Camry, Corolla'},
            {'sku': 'FLT-004', 'name': 'Transmission Filter', 'category': 'Filters', 'barcode': '1234567890404',
             'cost': '18.00', 'price': '36.99', 'stock': 48, 'min_stock': 15, 'brand': 'ACDelco', 'model': 'GM Vehicles'},

            # Cooling System
            {'sku': 'COL-001', 'name': 'Radiator Assembly', 'category': 'Cooling System', 'barcode': '1234567890501',
             'cost': '125.00', 'price': '249.99', 'stock': 15, 'min_stock': 5, 'brand': 'Spectra', 'model': 'Honda Civic'},
            {'sku': 'COL-002', 'name': 'Water Pump', 'category': 'Cooling System', 'barcode': '1234567890502',
             'cost': '48.00', 'price': '95.99', 'stock': 35, 'min_stock': 12, 'brand': 'Gates', 'model': 'Toyota Camry'},
            {'sku': 'COL-003', 'name': 'Thermostat', 'category': 'Cooling System', 'barcode': '1234567890503',
             'cost': '15.00', 'price': '32.99', 'stock': 68, 'min_stock': 20, 'brand': 'Stant', 'model': 'Universal'},
            {'sku': 'COL-004', 'name': 'Coolant Green (5L)', 'category': 'Cooling System', 'barcode': '1234567890504',
             'cost': '12.00', 'price': '25.99', 'stock': 85, 'min_stock': 25, 'brand': 'Prestone', 'model': 'Universal', 'uom': 'LITER'},
            {'sku': 'COL-005', 'name': 'Radiator Hose Upper', 'category': 'Cooling System', 'barcode': '1234567890505',
             'cost': '18.00', 'price': '36.99', 'stock': 42, 'min_stock': 15, 'brand': 'Dayco', 'model': 'Ford F-150'},

            # Oils & Fluids
            {'sku': 'OIL-001', 'name': 'Engine Oil 5W-30 (5L)', 'category': 'Oils & Fluids', 'barcode': '1234567890601',
             'cost': '22.00', 'price': '45.99', 'stock': 145, 'min_stock': 40, 'brand': 'Mobil 1', 'model': 'Universal', 'uom': 'LITER'},
            {'sku': 'OIL-002', 'name': 'Engine Oil 10W-40 (4L)', 'category': 'Oils & Fluids', 'barcode': '1234567890602',
             'cost': '18.00', 'price': '38.99', 'stock': 125, 'min_stock': 35, 'brand': 'Castrol', 'model': 'Universal', 'uom': 'LITER'},
            {'sku': 'OIL-003', 'name': 'Transmission Fluid ATF (1L)', 'category': 'Oils & Fluids', 'barcode': '1234567890603',
             'cost': '8.50', 'price': '18.99', 'stock': 95, 'min_stock': 25, 'brand': 'Valvoline', 'model': 'Universal', 'uom': 'LITER'},
            {'sku': 'OIL-004', 'name': 'Power Steering Fluid (1L)', 'category': 'Oils & Fluids', 'barcode': '1234567890604',
             'cost': '6.00', 'price': '13.99', 'stock': 78, 'min_stock': 20, 'brand': 'Lucas Oil', 'model': 'Universal', 'uom': 'LITER'},

            # Belts & Hoses
            {'sku': 'BLT-001', 'name': 'Serpentine Belt', 'category': 'Belts & Hoses', 'barcode': '1234567890701',
             'cost': '22.00', 'price': '45.99', 'stock': 65, 'min_stock': 20, 'brand': 'Gates', 'model': 'Toyota Camry'},
            {'sku': 'BLT-002', 'name': 'Timing Belt', 'category': 'Belts & Hoses', 'barcode': '1234567890702',
             'cost': '35.00', 'price': '69.99', 'stock': 42, 'min_stock': 15, 'brand': 'ContiTech', 'model': 'Honda Accord'},
            {'sku': 'BLT-003', 'name': 'Radiator Hose Kit', 'category': 'Belts & Hoses', 'barcode': '1234567890703',
             'cost': '28.00', 'price': '56.99', 'stock': 38, 'min_stock': 12, 'brand': 'Dayco', 'model': 'Universal', 'uom': 'SET'},

            # Lighting
            {'sku': 'LGT-001', 'name': 'Headlight Bulb H7', 'category': 'Lighting', 'barcode': '1234567890801',
             'cost': '12.00', 'price': '25.99', 'stock': 88, 'min_stock': 25, 'brand': 'Philips', 'model': 'Universal'},
            {'sku': 'LGT-002', 'name': 'LED Headlight Kit', 'category': 'Lighting', 'barcode': '1234567890802',
             'cost': '45.00', 'price': '89.99', 'stock': 32, 'min_stock': 10, 'brand': 'Auxbeam', 'model': 'Universal', 'uom': 'SET'},
            {'sku': 'LGT-003', 'name': 'Tail Light Assembly', 'category': 'Lighting', 'barcode': '1234567890803',
             'cost': '55.00', 'price': '109.99', 'stock': 24, 'min_stock': 8, 'brand': 'TYC', 'model': 'Honda Civic'},

            # Tires & Wheels
            {'sku': 'TIR-001', 'name': 'All Season Tire 195/65R15', 'category': 'Tires & Wheels', 'barcode': '1234567890901',
             'cost': '65.00', 'price': '129.99', 'stock': 48, 'min_stock': 16, 'brand': 'Michelin', 'model': 'Universal'},
            {'sku': 'TIR-002', 'name': 'Performance Tire 225/45R17', 'category': 'Tires & Wheels', 'barcode': '1234567890902',
             'cost': '95.00', 'price': '189.99', 'stock': 28, 'min_stock': 12, 'brand': 'Bridgestone', 'model': 'Sports Cars'},
            {'sku': 'TIR-003', 'name': 'Wheel Hub Assembly', 'category': 'Tires & Wheels', 'barcode': '1234567890903',
             'cost': '58.00', 'price': '115.99', 'stock': 35, 'min_stock': 12, 'brand': 'Timken', 'model': 'Honda Accord'},

            # Low stock items
            {'sku': 'ENG-099', 'name': 'Turbocharger Kit', 'category': 'Engine Parts', 'barcode': '1234567899999',
             'cost': '450.00', 'price': '899.99', 'stock': 3, 'min_stock': 5, 'brand': 'Garrett', 'model': 'WRX STI'},
            {'sku': 'BRK-099', 'name': 'ABS Module', 'category': 'Brake System', 'barcode': '1234567899998',
             'cost': '285.00', 'price': '565.00', 'stock': 2, 'min_stock': 5, 'brand': 'Bosch', 'model': 'BMW 5 Series'},
        ]

        products = {}
        for prod_data in products_data:
            product, created = Product.objects.get_or_create(
                sku=prod_data['sku'],
                defaults={
                    'name': prod_data['name'],
                    'category': categories[prod_data['category']],
                    'barcode': prod_data.get('barcode', ''),
                    'cost_price': Decimal(prod_data['cost']),
                    'selling_price': Decimal(prod_data['price']),
                    'current_stock': prod_data['stock'],
                    'minimum_stock_level': prod_data['min_stock'],
                    'brand': prod_data.get('brand', ''),
                    'model_compatibility': prod_data.get('model', ''),
                    'unit_of_measure': prod_data.get('uom', 'PIECE'),
                    'is_active': True,
                }
            )
            products[prod_data['sku']] = product
            if created:
                self.stdout.write(f'  Created product: {product.sku} - {product.name}')

        # Create Suppliers
        suppliers_data = [
            {
                'name': 'AutoZone Wholesale',
                'contact_person': 'John Smith',
                'email': 'john@autozone.com',
                'phone': '+1-555-0101',
                'address': '123 Auto Parts Blvd, Detroit, MI 48201'
            },
            {
                'name': 'O\'Reilly Parts Supply',
                'contact_person': 'Sarah Johnson',
                'email': 'sarah@oreilly.com',
                'phone': '+1-555-0102',
                'address': '456 Parts Avenue, Springfield, MO 65801'
            },
            {
                'name': 'NAPA Auto Parts Distributor',
                'contact_person': 'Mike Wilson',
                'email': 'mike@napaparts.com',
                'phone': '+1-555-0103',
                'address': '789 Distribution Way, Atlanta, GA 30301'
            },
            {
                'name': 'Advance Auto Parts',
                'contact_person': 'Emily Davis',
                'email': 'emily@advanceauto.com',
                'phone': '+1-555-0104',
                'address': '321 Supply Road, Raleigh, NC 27601'
            },
            {
                'name': 'Genuine Parts Company',
                'contact_person': 'Robert Martinez',
                'email': 'robert@genuineparts.com',
                'phone': '+1-555-0105',
                'address': '555 OEM Street, Houston, TX 77001'
            },
        ]

        suppliers = {}
        for supp_data in suppliers_data:
            supplier, created = Supplier.objects.get_or_create(
                name=supp_data['name'],
                defaults={
                    'contact_person': supp_data['contact_person'],
                    'email': supp_data['email'],
                    'phone': supp_data['phone'],
                    'address': supp_data['address'],
                    'is_active': True,
                }
            )
            suppliers[supp_data['name']] = supplier
            if created:
                self.stdout.write(f'  Created supplier: {supplier.name}')

        # Create Purchase Orders
        po_data = [
            {
                'po_number': 'PO-2024-001',
                'supplier': 'AutoZone Wholesale',
                'status': 'RECEIVED',
                'order_date': date.today() - timedelta(days=30),
                'items': [
                    {'sku': 'ENG-001', 'qty': 100, 'cost': '5.50'},
                    {'sku': 'BRK-001', 'qty': 50, 'cost': '28.00'},
                    {'sku': 'FLT-001', 'qty': 75, 'cost': '8.50'},
                ]
            },
            {
                'po_number': 'PO-2024-002',
                'supplier': 'O\'Reilly Parts Supply',
                'status': 'RECEIVED',
                'order_date': date.today() - timedelta(days=25),
                'items': [
                    {'sku': 'ELC-001', 'qty': 30, 'cost': '65.00'},
                    {'sku': 'OIL-001', 'qty': 100, 'cost': '22.00'},
                    {'sku': 'BRK-004', 'qty': 80, 'cost': '6.50'},
                ]
            },
            {
                'po_number': 'PO-2024-003',
                'supplier': 'NAPA Auto Parts Distributor',
                'status': 'PARTIAL',
                'order_date': date.today() - timedelta(days=15),
                'items': [
                    {'sku': 'SUS-001', 'qty': 40, 'cost': '55.00'},
                    {'sku': 'SUS-002', 'qty': 40, 'cost': '52.00'},
                    {'sku': 'COL-001', 'qty': 20, 'cost': '125.00'},
                ]
            },
            {
                'po_number': 'PO-2024-004',
                'supplier': 'Advance Auto Parts',
                'status': 'SUBMITTED',
                'order_date': date.today() - timedelta(days=5),
                'expected_delivery': date.today() + timedelta(days=10),
                'items': [
                    {'sku': 'ENG-002', 'qty': 60, 'cost': '18.00'},
                    {'sku': 'LGT-001', 'qty': 100, 'cost': '12.00'},
                    {'sku': 'TIR-001', 'qty': 40, 'cost': '65.00'},
                ]
            },
            {
                'po_number': 'PO-2024-005',
                'supplier': 'Genuine Parts Company',
                'status': 'DRAFT',
                'order_date': date.today(),
                'expected_delivery': date.today() + timedelta(days=14),
                'items': [
                    {'sku': 'ENG-099', 'qty': 10, 'cost': '450.00'},
                    {'sku': 'BRK-099', 'qty': 8, 'cost': '285.00'},
                    {'sku': 'ELC-002', 'qty': 15, 'cost': '145.00'},
                ]
            },
        ]

        for po in po_data:
            purchase_order, created = PurchaseOrder.objects.get_or_create(
                po_number=po['po_number'],
                defaults={
                    'supplier': suppliers[po['supplier']],
                    'status': po['status'],
                    'order_date': po['order_date'],
                    'expected_delivery_date': po.get('expected_delivery'),
                    'created_by': admin_user,
                }
            )
            
            if created:
                self.stdout.write(f'  Created PO: {purchase_order.po_number}')
                
                # Create PO Items
                for item in po['items']:
                    product = products[item['sku']]
                    received_qty = item['qty'] if po['status'] == 'RECEIVED' else (
                        int(item['qty'] * 0.6) if po['status'] == 'PARTIAL' else 0
                    )
                    
                    POItem.objects.create(
                        purchase_order=purchase_order,
                        product=product,
                        ordered_quantity=item['qty'],
                        received_quantity=received_qty,
                        unit_cost=Decimal(item['cost'])
                    )
                    self.stdout.write(f'    - Added item: {product.sku} x {item["qty"]}')

        self.stdout.write(self.style.SUCCESS('\n✓ Sample data created successfully!'))
        self.stdout.write(self.style.SUCCESS(f'✓ Categories: {Category.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'✓ Products: {Product.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'✓ Suppliers: {Supplier.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'✓ Purchase Orders: {PurchaseOrder.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'✓ PO Items: {POItem.objects.count()}'))
