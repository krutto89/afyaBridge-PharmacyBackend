from django.contrib import admin
from .models import Receipt


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display    = ['id_short', 'order_id', 'dispensed_by', 'payment_method',
                       'subtotal', 'discount', 'total', 'mpesa_ref',
                       'has_pdf', 'emailed_at', 'sms_sent_at', 'created_at']
    list_filter     = ['payment_method']
    search_fields   = ['mpesa_ref']
    readonly_fields = ['created_at', 'updated_at', 'emailed_at', 'sms_sent_at']
    date_hierarchy  = 'created_at'

    def id_short(self, obj):
        return f'REC-{str(obj.id)[:8].upper()}'
    id_short.short_description = 'Receipt ID'

    def has_pdf(self, obj):
        return bool(obj.pdf_path)
    has_pdf.boolean = True
    has_pdf.short_description = 'PDF Ready'

    fieldsets = (
        ('Order', {
            'fields': ('order_id', 'dispensed_by')
        }),
        ('Amounts', {
            'fields': ('subtotal', 'discount', 'total')
        }),
        ('Payment', {
            'fields': ('payment_method', 'mpesa_ref')
        }),
        ('Delivery', {
            'fields': ('pdf_path', 'emailed_at', 'sms_sent_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['regenerate_pdf']

    def regenerate_pdf(self, request, queryset):
        from apps.receipts.views import generate_pdf
        count = 0
        for receipt in queryset:
            try:
                filepath, filename = generate_pdf(receipt)
                receipt.pdf_path = f'receipts/{filename}'
                receipt.save()
                count += 1
            except Exception as e:
                self.message_user(request, f'Error on {receipt}: {e}', level='error')
        self.message_user(request, f'{count} receipt PDF(s) regenerated.')
    regenerate_pdf.short_description = 'Regenerate PDF for selected receipts'
