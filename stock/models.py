from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from inventory.models import Product


class StockTransaction(models.Model):
    """Stock movement history"""
    
    TRANSACTION_TYPE_CHOICES = [
        ('IN', 'Stock In'),
        ('OUT', 'Stock Out'),
        ('ADJUSTMENT', 'Adjustment'),
    ]
    
    REASON_CHOICES = [
        ('PURCHASE', 'Purchase Order Receipt'),
        ('SALE', 'Sale'),
        ('DAMAGED', 'Damaged'),
        ('LOST', 'Lost'),
        ('RECONCILIATION', 'Stock Reconciliation'),
        ('RETURN', 'Return'),
        ('MANUAL', 'Manual Adjustment'),
    ]
    
    partner = models.ForeignKey(
        'users.Partner',
        on_delete=models.CASCADE,
        related_name='stock_transactions',
        null=True,
        blank=True,
        help_text='Partner/tenant this stock transaction belongs to'
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='stock_transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    reason = models.CharField(max_length=30, choices=REASON_CHOICES)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    quantity_before = models.IntegerField()
    quantity_after = models.IntegerField()
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        null=True,
        blank=True,
        help_text='Cost per unit at time of transaction (for IN transactions)'
    )
    total_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        null=True,
        blank=True,
        help_text='Total cost (quantity × unit_cost)'
    )
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='PO number, Sale number, or other reference'
    )
    notes = models.TextField(blank=True, null=True)
    performed_by = models.ForeignKey('users.User', on_delete=models.PROTECT, related_name='stock_transactions')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'stock_transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['transaction_type']),
            models.Index(fields=['partner']),
        ]
    
    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.product.name} ({self.quantity})"


class ProductCostHistory(models.Model):
    """Track product cost price changes for auditing"""
    partner = models.ForeignKey(
        'users.Partner',
        on_delete=models.CASCADE,
        related_name='product_cost_histories',
        null=True,
        blank=True,
        help_text='Partner/tenant this cost history belongs to'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='cost_history'
    )
    old_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    new_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    stock_transaction = models.ForeignKey(
        StockTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cost_changes',
        help_text='The stock transaction that triggered this cost change'
    )
    reason = models.CharField(
        max_length=100,
        help_text='Reason for cost change'
    )
    changed_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='cost_changes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'product_cost_history'
        ordering = ['-created_at']
        verbose_name_plural = 'Product cost histories'
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['partner']),
        ]
    
    def __str__(self):
        return f"{self.product.name}: ₱{self.old_cost} → ₱{self.new_cost}"
    
    @property
    def cost_difference(self):
        """Calculate the difference between old and new cost"""
        return self.new_cost - self.old_cost
    
    @property
    def percentage_change(self):
        """Calculate the percentage change in cost"""
        if self.old_cost == 0:
            return Decimal('100.00') if self.new_cost > 0 else Decimal('0.00')
        return ((self.new_cost - self.old_cost) / self.old_cost) * 100
