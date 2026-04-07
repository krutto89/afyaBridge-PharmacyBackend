from rest_framework import serializers
from .models import Drug, StockBatch


class DrugSerializer(serializers.ModelSerializer):
    stock_status = serializers.ReadOnlyField()

    class Meta:
        model  = Drug
        fields = '__all__'
        read_only_fields = ['id', 'pharmacy_id', 'created_at', 'updated_at']

    def validate_unit_price(self, value):
        if value <= 0:
            raise serializers.ValidationError('Price must be greater than 0')
        return value


class StockBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model  = StockBatch
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class RestockSerializer(serializers.Serializer):
    quantity    = serializers.IntegerField(min_value=1)
    batch_no    = serializers.CharField(max_length=100)
    expiry_date = serializers.DateField()
    supplier_id = serializers.UUIDField(required=False, allow_null=True)