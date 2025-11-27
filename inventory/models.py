from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class Category(models.Model):
    """Product categories (Engine, Electrical, Accessories, etc.)"""
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'categories'
        ordering = ['name']
        verbose_name_plural = 'Categories'
    
    def __str__(self):
        return self.name


class Product(models.Model):
    """Product catalog with barcode support"""
    
    UOM_CHOICES = [
        ('PIECE', 'Piece'),
        ('BOX', 'Box'),
        ('SET', 'Set'),
        ('PAIR', 'Pair'),
        ('LITER', 'Liter'),
        ('KG', 'Kilogram'),
        ('METER', 'Meter'),
    ]
    
    sku = models.CharField(max_length=100, unique=True, help_text='Stock Keeping Unit / Part Number')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    brand = models.CharField(max_length=100, blank=True, null=True)
    model_compatibility = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='Compatible vehicle models'
    )
    unit_of_measure = models.CharField(max_length=20, choices=UOM_CHOICES, default='PIECE')
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    selling_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    minimum_stock_level = models.IntegerField(
        default=10,
        validators=[MinValueValidator(0)],
        help_text='Alert when stock falls below this level'
    )
    current_stock = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Current available stock quantity'
    )
    barcode = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True,
        help_text='Barcode value (manual entry or scanned)'
    )
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'products'
        ordering = ['name']
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['barcode']),
            models.Index(fields=['category']),
        ]
    
    def __str__(self):
        return f"{self.sku} - {self.name}"
    
    @property
    def is_low_stock(self):
        """Check if product is below minimum stock level"""
        return self.current_stock <= self.minimum_stock_level
    
    @property
    def stock_value(self):
        """Calculate total value of current stock"""
        return self.current_stock * self.cost_price


class Supplier(models.Model):
    """Supplier information"""
    
    name = models.CharField(max_length=255, unique=True)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'suppliers'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class PurchaseOrder(models.Model):
    """Purchase Order for procuring products"""
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('PARTIAL', 'Partially Received'),
        ('RECEIVED', 'Fully Received'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    po_number = models.CharField(max_length=50, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='purchase_orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    order_date = models.DateField()
    expected_delivery_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey('users.User', on_delete=models.PROTECT, related_name='created_orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'purchase_orders'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"PO-{self.po_number} - {self.supplier.name}"
    
    @property
    def total_amount(self):
        """Calculate total PO amount"""
        return sum(item.total_cost for item in self.items.all())
    
    @property
    def is_fully_received(self):
        """Check if all items are fully received"""
        return all(item.received_quantity >= item.ordered_quantity for item in self.items.all())


class POItem(models.Model):
    """Purchase Order Items"""
    
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='po_items')
    ordered_quantity = models.IntegerField(validators=[MinValueValidator(1)])
    received_quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    class Meta:
        db_table = 'po_items'
        unique_together = ['purchase_order', 'product']
    
    def __str__(self):
        return f"{self.purchase_order.po_number} - {self.product.name}"
    
    @property
    def total_cost(self):
        """Calculate total cost for this line item"""
        return self.ordered_quantity * self.unit_cost
    
    @property
    def remaining_quantity(self):
        """Calculate quantity yet to be received"""
        return self.ordered_quantity - self.received_quantity
