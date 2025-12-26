from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0001_initial'),
        ('expenses', '0004_assign_demo_partner'),
    ]

    operations = [
        migrations.AddField(
            model_name='expensecategory',
            name='store',
            field=models.ForeignKey(blank=True, help_text='Optional store this category belongs to', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='expense_categories', to='stores.store'),
        ),
        migrations.AddField(
            model_name='expense',
            name='store',
            field=models.ForeignKey(blank=True, help_text='Store this expense is tied to (optional)', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='expenses', to='stores.store'),
        ),
        migrations.AddConstraint(
            model_name='expensecategory',
            constraint=models.UniqueConstraint(fields=('partner', 'store', 'name'), name='unique_expense_category_per_partner_store'),
        ),
        migrations.AddIndex(
            model_name='expensecategory',
            index=models.Index(fields=['store'], name='expense_c_stor_i_072968_idx'),
        ),
        migrations.AddIndex(
            model_name='expense',
            index=models.Index(fields=['store'], name='expenses_store_i_29d9a0_idx'),
        ),
    ]
