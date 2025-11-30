# Generated manually - Create default Demo Partner and assign existing data

from django.db import migrations


def create_demo_partner(apps, schema_editor):
    """Create the Demo Partner and assign all existing users to it."""
    Partner = apps.get_model('users', 'Partner')
    User = apps.get_model('users', 'User')
    
    # Create Demo Partner
    demo_partner, created = Partner.objects.get_or_create(
        code='DEMO',
        defaults={
            'name': 'Demo Partner',
            'contact_email': 'demo@example.com',
            'is_active': True,
        }
    )
    
    # Assign all existing users without a partner to Demo Partner
    User.objects.filter(partner__isnull=True, is_super_admin=False).update(partner=demo_partner)


def reverse_demo_partner(apps, schema_editor):
    """Reverse the migration - remove partner from users."""
    User = apps.get_model('users', 'User')
    Partner = apps.get_model('users', 'Partner')
    
    # Set all users' partner to null
    User.objects.filter(partner__code='DEMO').update(partner=None)
    
    # Delete Demo Partner
    Partner.objects.filter(code='DEMO').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_add_partner_model'),
    ]

    operations = [
        migrations.RunPython(create_demo_partner, reverse_demo_partner),
    ]
