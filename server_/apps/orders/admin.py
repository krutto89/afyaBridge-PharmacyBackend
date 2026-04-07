from django.contrib import admin
from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display    = ['id_short', 'order_number', 'patient_name', 'pharmacy',
                       'status', 'priority', 'delivery_type',
                       'total_amount', 'payment_status', 'payment_method', 'created_at']
    list_filter     = ['status', 'priority', 'delivery_type',
                       'payment_status', 'payment_method', 'pharmacy']
    search_fields   = ['order_number', 'patient_name', 'patient_phone', 'mpesa_ref']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy  = 'created_at'

    def id_short(self, obj):
        return f'ORD-{str(obj.id)[:8].upper()}'
    id_short.short_description = 'Order ID'

    fieldsets = (
        ('Patient & Pharmacy', {
            'fields': ('pharmacy', 'patient_id', 'patient_name',
                       'patient_phone', 'patient_address', 'prescription_id')
        }),
        ('Order Details', {
            'fields': ('order_number', 'status', 'priority', 'delivery_type', 'total_amount')
        }),
        ('Payment', {
            'fields': ('payment_status', 'payment_method', 'mpesa_ref')
        }),
        ('Preparation', {
            'fields': ('prepared_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_ready']

    def mark_as_ready(self, request, queryset):
        queryset.update(status='ready')
        self.message_user(request, f'{queryset.count()} order(s) marked as ready.')
    mark_as_ready.short_description = 'Mark selected orders as Ready'
