from django.db import migrations


def create_default_stores(apps, schema_editor):
    Partner = apps.get_model('users', 'Partner')
    Store = apps.get_model('stores', 'Store')

    for partner in Partner.objects.all():
        if Store.objects.filter(partner_id=partner.id).exists():
            continue
        Store.objects.create(
            partner_id=partner.id,
            name=f"{partner.name} - Default",
            code=f"{partner.code}-DEFAULT",
            is_default=True,
            is_active=True,
        )


def reverse_noop(apps, schema_editor):
    # Do not delete stores on reverse to avoid data loss
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0001_initial'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_default_stores, reverse_noop),
    ]
