from django.db import models
from django.conf import settings


class ExpenseCategory(models.Model):
    """Categories for organizing expenses"""
    partner = models.ForeignKey(
        'users.Partner',
        on_delete=models.CASCADE,
        related_name='expense_categories',
        null=True,
        blank=True,
        help_text='Partner/tenant this expense category belongs to'
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#6366f1')  # Hex color for UI
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = 'Expense Categories'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['partner', 'name'],
                name='unique_expense_category_per_partner'
            )
        ]
    
    def __str__(self):
        return self.name


class Expense(models.Model):
    """Track business expenses"""
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('GCASH', 'GCash'),
        ('MAYA', 'Maya'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('CREDIT_CARD', 'Credit Card'),
        ('CHECK', 'Check'),
        ('OTHER', 'Other'),
    ]
    
    partner = models.ForeignKey(
        'users.Partner',
        on_delete=models.CASCADE,
        related_name='expenses',
        null=True,
        blank=True,
        help_text='Partner/tenant this expense belongs to'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.ForeignKey(
        ExpenseCategory, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='expenses'
    )
    payment_method = models.CharField(
        max_length=20, 
        choices=PAYMENT_METHOD_CHOICES, 
        default='CASH'
    )
    expense_date = models.DateField()
    receipt_number = models.CharField(max_length=100, blank=True)
    vendor = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    
    # Audit fields
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='expenses_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-expense_date', '-created_at']
    
    def __str__(self):
        return f"{self.title} - ₱{self.amount}"
