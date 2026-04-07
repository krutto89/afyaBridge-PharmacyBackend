from django.contrib import admin
from .models import Prescription


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = [
        'prescription_number',
        'patient_name',
        'doctor_name',
        'status',
        'priority',
        'issue_date',
        'created_at',
    ]
    list_filter  = ['status', 'priority']
    search_fields = ['patient_name', 'doctor_name', 'prescription_number']
    readonly_fields = ['created_at', 'updated_at', 'dispensed_at']
    ordering = ['-created_at']