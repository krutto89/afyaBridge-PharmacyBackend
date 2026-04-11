from rest_framework import serializers
from .models import Order, OrderItem, PDispatchedItem
from apps.prescriptions.models import Prescription
import json


class OrderItemFromPrescriptionSerializer(serializers.Serializer):
    name = serializers.CharField()
    dosage = serializers.CharField(required=False, allow_null=True)
    frequency = serializers.CharField(required=False, allow_null=True)
    duration = serializers.CharField(required=False, allow_null=True)
    instructions = serializers.CharField(required=False, allow_null=True)
    quantity = serializers.IntegerField(default=1)


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'drug_id', 'drug_name', 'dosage', 'frequency', 'quantity', 'unit_price']


class PDispatchedItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PDispatchedItem
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class OrderSerializer(serializers.ModelSerializer):
    order_id_short = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'order_id_short', 'order_number', 'prescription_id', 'pharmacy',
            'prepared_by', 'patient_id', 'patient_name', 'patient_phone', 'patient_address',
            'delivery_type', 'priority', 'status', 'total_amount', 'payment_status',
            'payment_method', 'mpesa_ref', 'created_at', 'updated_at', 'items'
        ]
        read_only_fields = ['id', 'order_number', 'pharmacy', 'prepared_by', 'created_at', 'updated_at']

    def get_order_id_short(self, obj):
        return f'ORD-{str(obj.id)[:8].upper()}'

    def get_items(self, obj):
        """Robust items retrieval: handles custom managers on Prescription + fallback"""
        if obj.prescription_id:
            try:
                # First try normal queryset (in case manager allows it)
                rx = Prescription.objects.get(id=obj.prescription_id)
            except Prescription.DoesNotExist:
                try:
                    # Bypass custom manager (this is the key fix)
                    rx = Prescription._base_manager.get(id=obj.prescription_id)
                except Prescription.DoesNotExist:
                    # Final fallback: raw SQL query (most reliable when managers hide records)
                    try:
                        from django.db import connection
                        with connection.cursor() as cursor:
                            cursor.execute(
                                "SELECT items FROM prescriptions WHERE id = %s",
                                [str(obj.prescription_id)]
                            )
                            row = cursor.fetchone()
                            if row and row[0]:
                                items_data = row[0]
                            else:
                                items_data = None
                    except Exception:
                        items_data = None

                    if items_data:
                        if isinstance(items_data, str):
                            try:
                                items_data = json.loads(items_data)
                            except json.JSONDecodeError:
                                items_data = []
                        if isinstance(items_data, list) and items_data:
                            return OrderItemFromPrescriptionSerializer(items_data, many=True).data

                    # If we reach here, prescription has no items or doesn't exist
                    return self._get_order_items_fallback(obj)

            # If we successfully got the prescription object
            items_data = getattr(rx, 'items', None) or []

            if isinstance(items_data, str):
                try:
                    items_data = json.loads(items_data)
                except json.JSONDecodeError:
                    items_data = []

            if isinstance(items_data, list) and items_data:
                return OrderItemFromPrescriptionSerializer(items_data, many=True).data

        # Fallback to OrderItem model if prescription failed or has no items
        return self._get_order_items_fallback(obj)

    def _get_order_items_fallback(self, obj):
        """Helper to get items directly from OrderItem table"""
        items = OrderItem.objects.filter(order_id=str(obj.id))
        if items.exists():
            return OrderItemSerializer(items, many=True).data
        return []