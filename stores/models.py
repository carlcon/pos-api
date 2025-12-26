from django.db import models


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
