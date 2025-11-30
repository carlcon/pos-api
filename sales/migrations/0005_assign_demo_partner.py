# Generated manually - Assign existing sales data to Demo Partner

from django.db import migrations


def assign_sales_to_demo_partner(apps, schema_editor):
    """Assign all existing sales data to Demo Partner."""
    Partner = apps.get_model('users', 'Partner')
    Sale = apps.get_model('sales', 'Sale')
    
    try:
        demo_partner = Partner.objects.get(code='DEMO')
    except Partner.DoesNotExist:
        return  # Demo partner doesn't exist yet
    
    # Assign all unassigned records to Demo Partner
    Sale.objects.filter(partner__isnull=True).update(partner=demo_partner)


def reverse_assignment(apps, schema_editor):
    """Remove partner assignment from sales data."""
    Sale = apps.get_model('sales', 'Sale')
    Sale.objects.all().update(partner=None)


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0004_add_partner_field'),
        ('users', '0003_create_demo_partner'),
    ]

    operations = [
        migrations.RunPython(assign_sales_to_demo_partner, reverse_assignment),
    ]
