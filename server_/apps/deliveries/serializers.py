from rest_framework import serializers
from .models import Delivery
import random
import string
import uuid


class DeliverySerializer(serializers.ModelSerializer):
    delivery_id_short = serializers.SerializerMethodField()
    package_number    = serializers.CharField(required=False)

    class Meta:
        model  = Delivery
        fields = '__all__'
        read_only_fields = [
            'id', 'otp_code', 'pickup_time', 'delivered_at', 'created_at', 'updated_at',
        ]

    def get_delivery_id_short(self, obj):
        return f'D-{str(obj.id)[:6].upper()}'

    def create(self, validated_data):
        validated_data['otp_code'] = ''.join(random.choices(string.digits, k=6))
        if not validated_data.get('package_number'):
            validated_data['package_number'] = f'PKG-{str(uuid.uuid4())[:8].upper()}'
        return super().create(validated_data)