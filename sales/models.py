from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from inventory.models import Product


class Sale(models.Model):
    """Sales transaction"""
    
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('CARD', 'Card'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('CHECK', 'Check'),
        ('CREDIT', 'Credit'),
    ]
    
    partner = models.ForeignKey(
        'users.Partner',
        on_delete=models.CASCADE,
        related_name='sales',
        null=True,
        blank=True,
        help_text='Partner/tenant this sale belongs to'
    )
    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.SET_NULL,
        related_name='sales',
        null=True,
        blank=True,
        help_text='Store where this sale occurred'
    )
    sale_number = models.CharField(max_length=50)
    customer_name = models.CharField(max_length=255, blank=True, null=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='CASH')
    is_wholesale = models.BooleanField(
        default=False,
        help_text='Whether this sale used wholesale pricing'
    )
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    notes = models.TextField(blank=True, null=True)
    cashier = models.ForeignKey('users.User', on_delete=models.PROTECT, related_name='sales')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'sales'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['sale_number']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['cashier']),
            models.Index(fields=['partner']),
            models.Index(fields=['store']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['partner', 'sale_number'],
                name='unique_sale_number_per_partner'
            )
        ]
    
    def __str__(self):
        return f"Sale-{self.sale_number} - {self.total_amount}"
    
    def calculate_total(self):
        """Calculate total amount after discount"""
        self.total_amount = self.subtotal - self.discount
        return self.total_amount


class SaleItem(models.Model):
    """Individual items in a sale"""
    
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='sale_items')
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Discount per item'
    )
    line_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    class Meta:
        db_table = 'sale_items'
        unique_together = ['sale', 'product']
    
    def __str__(self):
        return f"{self.sale.sale_number} - {self.product.name} x {self.quantity}"
    
    def calculate_line_total(self):
        """Calculate line total after discount"""
        self.line_total = (self.unit_price * self.quantity) - self.discount
        return self.line_total
