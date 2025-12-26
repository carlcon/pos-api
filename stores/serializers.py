from rest_framework import serializers
from .models import Store


class StoreSerializer(serializers.ModelSerializer):
    partner_name = serializers.CharField(source='partner.name', read_only=True)
    partner_code = serializers.CharField(source='partner.code', read_only=True)

    class Meta:
        model = Store
        fields = [
            'id', 'partner', 'partner_name', 'partner_code',
            'code', 'name', 'description', 'contact_email', 'contact_phone',
            'address', 'is_active', 'is_default', 'created_at', 'updated_at'
        ]
        read_only_fields = ['partner', 'is_default', 'created_at', 'updated_at']


class StoreCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = [
            'code', 'name', 'description', 'contact_email', 'contact_phone',
            'address', 'is_active'
        ]
