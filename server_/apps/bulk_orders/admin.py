from django.contrib import admin
from .models import Supplier, BulkOrder, BulkOrderItem


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display    = ['name', 'contact_name', 'email', 'phone', 'is_active', 'created_at']
    list_filter     = ['is_active']
    search_fields   = ['name', 'email', 'phone']
    readonly_fields = ['created_at', 'updated_at']


class BulkOrderItemInline(admin.TabularInline):
    model  = BulkOrderItem
    extra  = 1
    fields = ['drug_id', 'quantity_ordered', 'quantity_received',
              'unit_cost', 'batch_number', 'expiry_date']


@admin.register(BulkOrder)
class BulkOrderAdmin(admin.ModelAdmin):
    inlines         = [BulkOrderItemInline]
    list_display    = ['id_short', 'pharmacy', 'supplier', 'status',
                       'total_cost', 'expected_date', 'received_date', 'created_at']
    list_filter     = ['status', 'pharmacy', 'supplier']
    search_fields   = ['supplier__name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy  = 'created_at'

    def id_short(self, obj):
        return f'PO-{str(obj.id)[:8].upper()}'
    id_short.short_description = 'PO ID'

    fieldsets = (
        ('Purchase Order', {
            'fields': ('pharmacy', 'supplier', 'status', 'total_cost', 'notes')
        }),
        ('Dates', {
            'fields': ('expected_date', 'received_date', 'created_by', 'created_at', 'updated_at')
        }),
    )

    actions = ['mark_as_received']

    def mark_as_received(self, request, queryset):
        queryset.update(status='received')
        self.message_user(request, f'{queryset.count()} PO(s) marked as received.')
    mark_as_received.short_description = 'Mark selected POs as Received'


@admin.register(BulkOrderItem)
class BulkOrderItemAdmin(admin.ModelAdmin):
    list_display  = ['bulk_order', 'drug_id', 'quantity_ordered',
                     'quantity_received', 'unit_cost', 'batch_number', 'expiry_date']
    search_fields = ['batch_number']
    list_filter   = ['expiry_date']
