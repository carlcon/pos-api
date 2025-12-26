from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0001_initial'),
        ('sales', '0005_assign_demo_partner'),
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='store',
            field=models.ForeignKey(blank=True, help_text='Store where this sale occurred', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sales', to='stores.store'),
        ),
        migrations.AddIndex(
            model_name='sale',
            index=models.Index(fields=['store'], name='sales_store_idx'),
        ),
    ]
