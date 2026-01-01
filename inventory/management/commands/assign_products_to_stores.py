from django.core.management.base import BaseCommand
from inventory.models import Product
from stores.models import Store
from users.models import Partner


class Command(BaseCommand):
    help = 'Assign all products to their partner stores'

    def add_arguments(self, parser):
        parser.add_argument(
            '--partner-code',
            type=str,
            help='Partner code to filter (e.g., DEMO001)',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Assign products for all partners',
        )

    def handle(self, *args, **options):
        partner_code = options.get('partner_code')
        assign_all = options.get('all')

        if not partner_code and not assign_all:
            self.stdout.write(
                self.style.ERROR('Please specify --partner-code or --all')
            )
            return

        # Get partners to process
        if partner_code:
            partners = Partner.objects.filter(code=partner_code)
            if not partners.exists():
                self.stdout.write(
                    self.style.ERROR(f'Partner with code "{partner_code}" not found')
                )
                return
        else:
            partners = Partner.objects.all()

        total_assigned = 0

        for partner in partners:
            self.stdout.write(f'\nProcessing partner: {partner.name} ({partner.code})')
            
            # Get all products for this partner
            products = Product.objects.filter(partner=partner)
            product_count = products.count()
            
            if product_count == 0:
                self.stdout.write(
                    self.style.WARNING(f'  No products found for {partner.name}')
                )
                continue

            # Get all stores for this partner
            stores = Store.objects.filter(partner=partner, is_active=True)
            store_count = stores.count()
            
            if store_count == 0:
                self.stdout.write(
                    self.style.WARNING(f'  No active stores found for {partner.name}')
                )
                continue

            self.stdout.write(
                f'  Found {product_count} products and {store_count} stores'
            )

            # Assign all products to all stores
            assigned_count = 0
            for product in products:
                # Get current store assignments
                current_stores = set(product.available_stores.all())
                target_stores = set(stores)
                
                # Only add stores that aren't already assigned
                new_stores = target_stores - current_stores
                
                if new_stores:
                    product.available_stores.add(*new_stores)
                    assigned_count += 1
                    self.stdout.write(
                        f'    ✓ Assigned "{product.name}" to {len(new_stores)} new stores'
                    )

            if assigned_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  Successfully updated {assigned_count} products for {partner.name}'
                    )
                )
                total_assigned += assigned_count
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  All products already assigned to stores for {partner.name}'
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Complete! Updated {total_assigned} products across {partners.count()} partner(s)'
            )
        )
