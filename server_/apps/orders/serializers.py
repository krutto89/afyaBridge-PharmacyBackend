from rest_framework import serializers
from .models import Order, OrderItem, PDispatchedItem
import uuid


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model  = OrderItem
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class OrderSerializer(serializers.ModelSerializer):
    order_id_short = serializers.SerializerMethodField()
    items          = serializers.SerializerMethodField()  # ← changed

    class Meta:
        model  = Order
        fields = '__all__'
        read_only_fields = ['id', 'pharmacy_id', 'prepared_by', 'created_at', 'updated_at']

    def get_order_id_short(self, obj):
        return f'ORD-{str(obj.id)[:8].upper()}'

    def get_items(self, obj):                                        # ← add this
        items = OrderItem.objects.filter(order_id=str(obj.id))
        return OrderItemSerializer(items, many=True).data

    def validate_total_amount(self, value):
        if value < 0:
            raise serializers.ValidationError('Total amount cannot be negative')
        return value

    def create(self, validated_data):
        if not validated_data.get('order_number'):
            validated_data['order_number'] = f'ORD-{str(uuid.uuid4())[:8].upper()}'
        return super().create(validated_data)


class PDispatchedItemSerializer(serializers.ModelSerializer):
    class Meta:
        model  = PDispatchedItem
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']