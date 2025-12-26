from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0001_initial'),
        ('stock', '0006_productcosthistory_partner_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='productcosthistory',
            name='store',
            field=models.ForeignKey(blank=True, help_text='Store context for this cost change (optional)', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='product_cost_histories', to='stores.store'),
        ),
        migrations.AddField(
            model_name='stocktransaction',
            name='store',
            field=models.ForeignKey(blank=True, help_text='Store associated with this stock movement', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='stock_transactions', to='stores.store'),
        ),
        migrations.AddIndex(
            model_name='productcosthistory',
            index=models.Index(fields=['store'], name='product_cos_store_i_3f4f97_idx'),
        ),
        migrations.AddIndex(
            model_name='stocktransaction',
            index=models.Index(fields=['store'], name='stock_trans_store_i_6c7cd2_idx'),
        ),
    ]
