from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Store',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(help_text='Store code unique within partner', max_length=50)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('contact_email', models.EmailField(blank=True, max_length=254, null=True)),
                ('contact_phone', models.CharField(blank=True, max_length=20, null=True)),
                ('address', models.TextField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('is_default', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('partner', models.ForeignKey(help_text='Partner/tenant that owns this store', on_delete=django.db.models.deletion.PROTECT, related_name='stores', to='users.partner')),
            ],
            options={
                'db_table': 'stores',
                'ordering': ['name'],
            },
        ),
        migrations.AddIndex(
            model_name='store',
            index=models.Index(fields=['partner'], name='stores_partn_3cddbe_idx'),
        ),
        migrations.AddIndex(
            model_name='store',
            index=models.Index(fields=['is_active'], name='stores_is_ac_b6fc15_idx'),
        ),
        migrations.AddConstraint(
            model_name='store',
            constraint=models.UniqueConstraint(fields=('partner', 'code'), name='unique_store_code_per_partner'),
        ),
        migrations.AddConstraint(
            model_name='store',
            constraint=models.UniqueConstraint(fields=('partner', 'name'), name='unique_store_name_per_partner'),
        ),
    ]
