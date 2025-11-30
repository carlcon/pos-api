# Generated manually - Assign existing inventory data to Demo Partner

from django.db import migrations


def assign_inventory_to_demo_partner(apps, schema_editor):
    """Assign all existing inventory data to Demo Partner."""
    Partner = apps.get_model('users', 'Partner')
    Category = apps.get_model('inventory', 'Category')
    Product = apps.get_model('inventory', 'Product')
    Supplier = apps.get_model('inventory', 'Supplier')
    PurchaseOrder = apps.get_model('inventory', 'PurchaseOrder')
    
    try:
        demo_partner = Partner.objects.get(code='DEMO')
    except Partner.DoesNotExist:
        return  # Demo partner doesn't exist yet
    
    # Assign all unassigned records to Demo Partner
    Category.objects.filter(partner__isnull=True).update(partner=demo_partner)
    Product.objects.filter(partner__isnull=True).update(partner=demo_partner)
    Supplier.objects.filter(partner__isnull=True).update(partner=demo_partner)
    PurchaseOrder.objects.filter(partner__isnull=True).update(partner=demo_partner)


def reverse_assignment(apps, schema_editor):
    """Remove partner assignment from inventory data."""
    Category = apps.get_model('inventory', 'Category')
    Product = apps.get_model('inventory', 'Product')
    Supplier = apps.get_model('inventory', 'Supplier')
    PurchaseOrder = apps.get_model('inventory', 'PurchaseOrder')
    
    Category.objects.all().update(partner=None)
    Product.objects.all().update(partner=None)
    Supplier.objects.all().update(partner=None)
    PurchaseOrder.objects.all().update(partner=None)


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0004_add_partner_field'),
        ('users', '0003_create_demo_partner'),
    ]

    operations = [
        migrations.RunPython(assign_inventory_to_demo_partner, reverse_assignment),
    ]
