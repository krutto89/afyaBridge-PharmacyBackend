# apps/patients/admin.py
from django.contrib import admin
from .models import Patient, PatientPrescription, RefillRequest, MpesaTransaction

admin.site.register(Patient)
admin.site.register(PatientPrescription)
admin.site.register(RefillRequest)

@admin.register(MpesaTransaction)
class MpesaTransactionAdmin(admin.ModelAdmin):
    list_display  = ['patient', 'amount', 'status', 'mpesa_receipt_no', 'initiated_at']
    list_filter   = ['status']
    readonly_fields = ['initiated_at', 'completed_at']
