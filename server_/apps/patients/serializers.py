# apps/patients/serializers.py
from rest_framework import serializers
from .models import Patient, PatientPrescription, RefillRequest, MpesaTransaction
from apps.settings_module.models import Pharmacy
from apps.prescriptions.models import Prescription


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Patient
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class PatientPrescriptionSerializer(serializers.ModelSerializer):
    patient_name     = serializers.CharField(source='patient.full_name', read_only=True)
    prescription_ref = serializers.SerializerMethodField()
    drug_list        = serializers.SerializerMethodField()

    class Meta:
        model  = PatientPrescription
        fields = '__all__'
        read_only_fields = ['id', 'created_at']

    def get_prescription_ref(self, obj):
        return f'RX-{str(obj.prescription_id)[:8].upper()}'

    def get_drug_list(self, obj):
        # Return the list of drug names from prescription items
        items = obj.prescription.items
        return [{'drug': i.get('drug_name'), 'quantity': i.get('quantity'), 'dosage': i.get('dosage')} for i in items]


class NearbyPharmacySerializer(serializers.ModelSerializer):
    """
    Pharmacy data returned to patient for nearby/map views.
    Includes distance — calculated in the view, injected here.
    """
    distance_km    = serializers.SerializerMethodField()
    logo_url       = serializers.SerializerMethodField()
    is_open_now    = serializers.SerializerMethodField()

    class Meta:
        model  = Pharmacy
        fields = ['id', 'name', 'address_line1', 'county', 'sub_county',
                  'gps_lat', 'gps_lng', 'phone', 'logo_url',
                  'is_24hr', 'distance_km', 'is_open_now']

    def get_distance_km(self, obj):
        # Injected by the view after calculation
        return getattr(obj, '_distance_km', None)

    def get_logo_url(self, obj):
        request = self.context.get('request')
        if obj.logo and request:
            return request.build_absolute_uri(obj.logo.url)
        return None

    def get_is_open_now(self, obj):
        from django.utils import timezone
        import datetime
        now       = timezone.localtime()
        day_map   = {0:'MON',1:'TUE',2:'WED',3:'THU',4:'FRI',5:'SAT',6:'SUN'}
        today_key = day_map[now.weekday()]
        if obj.is_24hr:
            return True
        hours = obj.hours.filter(day_of_week=today_key, is_closed=False).first()
        if not hours:
            return False
        return hours.open_time <= now.time() <= hours.close_time


class RefillRequestSerializer(serializers.ModelSerializer):
    pharmacy_name = serializers.CharField(
        source='selected_pharmacy.name', read_only=True
    )
    prescription_ref = serializers.SerializerMethodField()

    class Meta:
        model  = RefillRequest
        fields = '__all__'
        read_only_fields = ['id', 'patient', 'total_amount',
                            'created_at', 'updated_at']

    def get_prescription_ref(self, obj):
        rx = obj.patient_prescription.prescription
        return f'RX-{str(rx.id)[:8].upper()}'


class RefillSummarySerializer(serializers.ModelSerializer):
    """Detailed summary shown before payment"""
    pharmacy       = NearbyPharmacySerializer(source='selected_pharmacy', read_only=True)
    items          = serializers.SerializerMethodField()
    prescription_ref = serializers.SerializerMethodField()

    class Meta:
        model  = RefillRequest
        fields = ['id', 'status', 'delivery_type', 'delivery_address',
                  'total_amount', 'pharmacy', 'items', 'prescription_ref',
                  'created_at']

    def get_items(self, obj):
        items = obj.patient_prescription.prescription.items
        return [{'drug': i.get('drug_name'), 'quantity': i.get('quantity'), 'dosage': i.get('dosage'), 'duration_days': i.get('duration_days')}
                for i in items]

    def get_prescription_ref(self, obj):
        rx = obj.patient_prescription.prescription
        return f'RX-{str(rx.id)[:8].upper()}'


class MpesaPaySerializer(serializers.Serializer):
    """Payload to initiate STK Push"""
    phone  = serializers.CharField(max_length=20)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)


class MpesaCallbackSerializer(serializers.Serializer):
    """
    Receives Safaricom callback — structure is defined by Safaricom,
    not by us. We just parse it.
    """
    Body = serializers.DictField()