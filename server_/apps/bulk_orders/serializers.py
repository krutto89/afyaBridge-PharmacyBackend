from rest_framework import serializers
from .models import Supplier, BulkOrder, BulkOrderItem


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Supplier
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_email(self, value):
        if value and '@' not in value:
            raise serializers.ValidationError('Enter a valid email address')
        return value


class BulkOrderItemSerializer(serializers.ModelSerializer):
    line_total = serializers.SerializerMethodField()

    class Meta:
        model  = BulkOrderItem
        fields = '__all__'
        read_only_fields = ['id']

    def get_line_total(self, obj):
        return float(obj.quantity_ordered * obj.unit_cost)


class BulkOrderSerializer(serializers.ModelSerializer):
    items         = BulkOrderItemSerializer(many=True, read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    po_id_short   = serializers.SerializerMethodField()

    class Meta:
        model  = BulkOrder
        fields = '__all__'
        read_only_fields = [
            'id', 'pharmacy', 'created_by', 'received_date', 'created_at', 'updated_at',
        ]

    def get_po_id_short(self, obj):
        return f'PO-{str(obj.id)[:8].upper()}'
