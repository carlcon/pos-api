from rest_framework import serializers
from .models import Store


class StoreSerializer(serializers.ModelSerializer):
    partner_name = serializers.CharField(source='partner.name', read_only=True)
    partner_code = serializers.CharField(source='partner.code', read_only=True)
    admin_count = serializers.IntegerField(read_only=True)
    cashier_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Store
        fields = [
            'id', 'partner', 'partner_name', 'partner_code',
            'code', 'name', 'description', 'contact_email', 'contact_phone',
            'address', 'is_active', 'is_default', 'created_at', 'updated_at',
            'admin_count', 'cashier_count',
            'auto_print_receipt', 'printer_name', 'receipt_template',
        ]
        read_only_fields = ['partner', 'is_default', 'created_at', 'updated_at', 'admin_count', 'cashier_count']


class StoreCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = [
            'code', 'name', 'description', 'contact_email', 'contact_phone',
            'address', 'is_active', 'auto_print_receipt', 'printer_name',
        ]


class StoreUserSerializer(serializers.Serializer):
    """Serializer for Store Admin and Cashier users"""
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    role = serializers.CharField(read_only=True)
    is_active = serializers.BooleanField(default=True)
    sms_phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    created_at = serializers.DateTimeField(source='date_joined', read_only=True)


class StoreUserCreateSerializer(serializers.Serializer):
    """Serializer for creating Store Admin or Cashier users"""
    email = serializers.EmailField(required=False, allow_blank=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, required=False, default='Admin1234@')
    is_active = serializers.BooleanField(default=True)
    sms_phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class StoreUserUpdateSerializer(serializers.Serializer):
    """Serializer for updating Store Admin or Cashier users"""
    email = serializers.EmailField(required=False, allow_blank=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)
    sms_phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class StoreUserPasswordResetSerializer(serializers.Serializer):
    """Serializer for resetting store user password"""
    new_password = serializers.CharField(write_only=True, min_length=8)
