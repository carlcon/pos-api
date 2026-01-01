from django.db import models


DEFAULT_RECEIPT_TEMPLATE = """
=====================================
           {{store_name}}
=====================================
{{store_address}}
Tel: {{store_phone}}

Receipt #: {{sale_number}}
Date: {{date}}
Cashier: {{cashier}}
-------------------------------------
ITEMS:
{{items}}
-------------------------------------
Subtotal:          {{subtotal}}
Discount:          {{discount}}
-------------------------------------
TOTAL:             {{total}}
-------------------------------------
Payment: {{payment_method}}
=====================================
     Thank you for your purchase!
=====================================
"""


class Store(models.Model):
    partner = models.ForeignKey(
        'users.Partner',
        on_delete=models.PROTECT,
        related_name='stores',
        help_text='Partner/tenant that owns this store'
    )
    code = models.CharField(max_length=50, help_text='Store code unique within partner')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Receipt settings
    auto_print_receipt = models.BooleanField(
        default=False,
        help_text='Automatically print receipt after sale completion'
    )
    printer_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='Name of the printer to use for receipts'
    )
    receipt_template = models.TextField(
        default=DEFAULT_RECEIPT_TEMPLATE,
        help_text='Receipt template with placeholders (editable via Django admin)'
    )

    class Meta:
        db_table = 'stores'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['partner', 'code'], name='unique_store_code_per_partner'),
            models.UniqueConstraint(fields=['partner', 'name'], name='unique_store_name_per_partner'),
        ]
        indexes = [
            models.Index(fields=['partner']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"
    
    def render_receipt(self, sale):
        """Render receipt from template with sale data."""
        from django.utils import timezone
        
        # Build items list
        items_text = ""
        for item in sale.items.all():
            items_text += f"{item.product.name}\n"
            items_text += f"  {item.quantity} x {item.unit_price:.2f} = {item.line_total:.2f}\n"
        
        # Replace placeholders
        receipt = self.receipt_template
        receipt = receipt.replace('{{store_name}}', self.name)
        receipt = receipt.replace('{{store_address}}', self.address or '')
        receipt = receipt.replace('{{store_phone}}', self.contact_phone or '')
        receipt = receipt.replace('{{sale_number}}', sale.sale_number)
        receipt = receipt.replace('{{date}}', sale.created_at.strftime('%Y-%m-%d %H:%M:%S'))
        receipt = receipt.replace('{{cashier}}', sale.cashier.username if sale.cashier else 'N/A')
        receipt = receipt.replace('{{items}}', items_text)
        receipt = receipt.replace('{{subtotal}}', f"{sale.subtotal:.2f}")
        receipt = receipt.replace('{{discount}}', f"{sale.discount:.2f}")
        receipt = receipt.replace('{{total}}', f"{sale.total_amount:.2f}")
        receipt = receipt.replace('{{payment_method}}', sale.get_payment_method_display())
        
        return receipt
