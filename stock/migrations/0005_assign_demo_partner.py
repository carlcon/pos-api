# Generated manually - Assign existing stock data to Demo Partner

from django.db import migrations


def assign_stock_to_demo_partner(apps, schema_editor):
    """Assign all existing stock data to Demo Partner."""
    Partner = apps.get_model('users', 'Partner')
    StockTransaction = apps.get_model('stock', 'StockTransaction')
    
    try:
        demo_partner = Partner.objects.get(code='DEMO')
    except Partner.DoesNotExist:
        return  # Demo partner doesn't exist yet
    
    # Assign all unassigned records to Demo Partner
    StockTransaction.objects.filter(partner__isnull=True).update(partner=demo_partner)


def reverse_assignment(apps, schema_editor):
    """Remove partner assignment from stock data."""
    StockTransaction = apps.get_model('stock', 'StockTransaction')
    StockTransaction.objects.all().update(partner=None)


class Migration(migrations.Migration):

    dependencies = [
        ('stock', '0004_add_partner_field'),
        ('users', '0003_create_demo_partner'),
    ]

    operations = [
        migrations.RunPython(assign_stock_to_demo_partner, reverse_assignment),
    ]
