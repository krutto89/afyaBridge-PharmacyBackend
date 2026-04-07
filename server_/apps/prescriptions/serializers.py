from rest_framework import serializers
from django.utils import timezone
from .models import Prescription


class PrescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Prescription
        fields = '__all__'
        read_only_fields = [
            'id', 'prescription_number', 'pharmacy_id', 'dispensed_by',
            'dispensed_at', 'created_at', 'updated_at',
            'patient_name', 'patient_phone', 'patient_address', 'doctor_name',
        ]

    def validate_expiry_date(self, value):
        if value and value < timezone.now().date():
            raise serializers.ValidationError('Prescription has expired')
        return value

    def validate_items(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('items must be a list')
        for item in value:
            if not isinstance(item, dict):
                raise serializers.ValidationError('Each item must be a dictionary')
        return value


class DispenseSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True)