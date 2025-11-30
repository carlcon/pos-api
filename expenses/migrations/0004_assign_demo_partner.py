# Generated manually - Assign existing expenses data to Demo Partner

from django.db import migrations


def assign_expenses_to_demo_partner(apps, schema_editor):
    """Assign all existing expenses data to Demo Partner."""
    Partner = apps.get_model('users', 'Partner')
    Expense = apps.get_model('expenses', 'Expense')
    ExpenseCategory = apps.get_model('expenses', 'ExpenseCategory')
    
    try:
        demo_partner = Partner.objects.get(code='DEMO')
    except Partner.DoesNotExist:
        return  # Demo partner doesn't exist yet
    
    # Assign all unassigned records to Demo Partner
    Expense.objects.filter(partner__isnull=True).update(partner=demo_partner)
    ExpenseCategory.objects.filter(partner__isnull=True).update(partner=demo_partner)


def reverse_assignment(apps, schema_editor):
    """Remove partner assignment from expenses data."""
    Expense = apps.get_model('expenses', 'Expense')
    ExpenseCategory = apps.get_model('expenses', 'ExpenseCategory')
    
    Expense.objects.all().update(partner=None)
    ExpenseCategory.objects.all().update(partner=None)


class Migration(migrations.Migration):

    dependencies = [
        ('expenses', '0003_add_partner_field'),
        ('users', '0003_create_demo_partner'),
    ]

    operations = [
        migrations.RunPython(assign_expenses_to_demo_partner, reverse_assignment),
    ]
