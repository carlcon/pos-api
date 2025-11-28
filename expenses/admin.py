from django.contrib import admin
from .models import Expense, ExpenseCategory


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'color', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['title', 'amount', 'category', 'payment_method', 
                   'expense_date', 'vendor', 'created_by', 'created_at']
    list_filter = ['payment_method', 'category', 'expense_date', 'created_at']
    search_fields = ['title', 'description', 'vendor', 'receipt_number']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['created_by']
    date_hierarchy = 'expense_date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'amount', 'category')
        }),
        ('Payment Details', {
            'fields': ('payment_method', 'expense_date', 'receipt_number', 'vendor')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

