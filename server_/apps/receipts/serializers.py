from rest_framework import serializers
from .models import Receipt


class ReceiptSerializer(serializers.ModelSerializer):
    receipt_id_short = serializers.SerializerMethodField()
    has_pdf          = serializers.SerializerMethodField()

    class Meta:
        model  = Receipt
        fields = '__all__'
        read_only_fields = [
            'id', 'dispensed_by', 'pdf_path',
            'emailed_at', 'sms_sent_at', 'created_at', 'updated_at',
        ]

    def get_receipt_id_short(self, obj):
        return f'REC-{str(obj.id)[:8].upper()}'

    def get_has_pdf(self, obj):
        return bool(obj.pdf_path)
