from django.contrib import admin
from .models import Drug, StockBatch


@admin.register(Drug)
class DrugAdmin(admin.ModelAdmin):
    list_display = [
        'drug_name',
        'category',
        'unit_price',
        'quantity_in_stock',
        'stock_status',
        'reorder_level',
        'critical_level',
        'requires_rx',
        'is_active',
    ]
    list_filter   = ['category', 'requires_rx', 'is_active', 'unit']
    search_fields = ['drug_name', 'generic_name']
    readonly_fields = ['created_at', 'updated_at']

    def stock_status(self, obj):
        return obj.stock_status
    stock_status.short_description = 'Stock Status'

    fieldsets = (
        ('Drug Details', {
            'fields': ('pharmacy_id', 'drug_name', 'generic_name', 'category', 'unit')
        }),
        ('Pricing & Stock', {
            'fields': ('unit_price', 'quantity_in_stock', 'reorder_level', 'critical_level')
        }),
        ('Settings', {
            'fields': ('requires_rx', 'is_active', 'created_at', 'updated_at')
        }),
    )


@admin.register(StockBatch)
class StockBatchAdmin(admin.ModelAdmin):
    list_display = [
        'drug_id',
        'batch_number',
        'quantity_received',
        'quantity_remaining',
        'expiry_date',
        'received_by',
    ]
    list_filter   = ['expiry_date']
    search_fields = ['batch_number', 'drug_id']
    date_hierarchy = 'expiry_date'