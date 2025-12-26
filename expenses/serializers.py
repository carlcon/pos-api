from rest_framework import serializers
from .models import Expense, ExpenseCategory


class ExpenseCategorySerializer(serializers.ModelSerializer):
    expense_count = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()
    store_name = serializers.CharField(source='store.name', read_only=True)
    
    class Meta:
        model = ExpenseCategory
        fields = [
            'id', 'name', 'description', 'color', 'is_active',
            'store', 'store_name', 'expense_count', 'total_amount', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_expense_count(self, obj):
        return obj.expenses.count()
    
    def get_total_amount(self, obj):
        total = obj.expenses.aggregate(total=serializers.models.Sum('amount'))['total']
        return float(total) if total else 0


class ExpenseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_color = serializers.CharField(source='category.color', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    
    class Meta:
        model = Expense
        fields = [
            'id', 'title', 'description', 'amount', 'category', 'category_name', 
            'category_color', 'payment_method', 'payment_method_display', 
            'expense_date', 'receipt_number', 'vendor', 'notes', 
            'created_by', 'created_by_username', 'store', 'store_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']


class ExpenseCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = [
            'title', 'description', 'amount', 'category', 'payment_method',
            'expense_date', 'receipt_number', 'vendor', 'notes', 'store'
        ]
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value


class ExpenseStatsSerializer(serializers.Serializer):
    """Serializer for expense statistics"""
    total_expenses = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_count = serializers.IntegerField()
    this_month_total = serializers.DecimalField(max_digits=12, decimal_places=2)
    last_month_total = serializers.DecimalField(max_digits=12, decimal_places=2)
    by_category = serializers.ListField()
    by_payment_method = serializers.ListField()
