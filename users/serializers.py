from rest_framework import serializers
from .models import User, Partner


class PartnerSerializer(serializers.ModelSerializer):
    """Serializer for Partner model"""
    user_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Partner
        fields = [
            'id', 'name', 'code', 'contact_email', 'contact_phone',
            'address', 'is_active', 'user_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_user_count(self, obj):
        return obj.users.count()


class PartnerMinimalSerializer(serializers.ModelSerializer):
    """Minimal serializer for Partner (used in nested representations)"""
    
    class Meta:
        model = Partner
        fields = ['id', 'name', 'code']


class StoreMinimalSerializer(serializers.ModelSerializer):
    """Minimal serializer for Store (used in nested representations)"""
    
    class Meta:
        from stores.models import Store
        model = Store
        fields = ['id', 'name', 'code']


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    partner = PartnerMinimalSerializer(read_only=True)
    assigned_store = StoreMinimalSerializer(read_only=True)
    partner_id = serializers.PrimaryKeyRelatedField(
        queryset=Partner.objects.all(),
        source='partner',
        write_only=True,
        required=False,
        allow_null=True
    )
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'phone', 'employee_id', 'is_active_employee',
            'is_active', 'is_super_admin', 'partner', 'partner_id',
            'assigned_store', 'date_joined', 'last_login'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new users"""
    password = serializers.CharField(write_only=True, min_length=8)
    partner_id = serializers.PrimaryKeyRelatedField(
        queryset=Partner.objects.all(),
        source='partner',
        required=False,
        allow_null=True
    )
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'first_name', 'last_name',
            'role', 'phone', 'employee_id', 'is_active_employee',
            'is_super_admin', 'partner_id'
        ]
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user details"""
    partner_id = serializers.PrimaryKeyRelatedField(
        queryset=Partner.objects.all(),
        source='partner',
        required=False,
        allow_null=True
    )
    
    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'role',
            'phone', 'employee_id', 'is_active_employee', 'is_active',
            'is_super_admin', 'partner_id'
        ]


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change"""
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
