from django.contrib import admin
from .models import Delivery


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display    = ['id_short', 'package_number', 'order_id', 'rider_id',
                       'status', 'delivery_zone', 'pickup_time', 'delivered_at']
    list_filter     = ['status', 'delivery_zone', 'accept_status']
    search_fields   = ['package_number', 'delivery_zone', 'dropoff_location']
    readonly_fields = ['otp_code', 'created_at', 'updated_at', 'pickup_time', 'delivered_at']
    date_hierarchy  = 'created_at'

    def id_short(self, obj):
        return f'D-{str(obj.id)[:6].upper()}'
    id_short.short_description = 'Delivery ID'

    fieldsets = (
        ('Delivery Info', {
            'fields': ('package_number', 'order_id', 'rider_id', 'status', 'accept_status')
        }),
        ('Pickup', {
            'fields': ('pickup_location', 'pickup_lat', 'pickup_lng',
                       'pickup_contact', 'pickup_time')
        }),
        ('Dropoff', {
            'fields': ('dropoff_location', 'dropoff_lat', 'dropoff_lng', 'receiver_contact')
        }),
        ('Details', {
            'fields': ('requirement', 'estimated_delivery_time', 'distance',
                       'charges', 'delivery_zone', 'delivery_notes')
        }),
        ('Confirmation', {
            'fields': ('otp_code', 'delivered_at', 'date_approved'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_delivered']

    def mark_as_delivered(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='delivered', delivered_at=timezone.now())
        self.message_user(request, f'{queryset.count()} delivery(ies) marked as delivered.')
    mark_as_delivered.short_description = 'Mark selected deliveries as Delivered'
