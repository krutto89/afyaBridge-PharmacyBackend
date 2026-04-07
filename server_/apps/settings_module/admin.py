from django.contrib import admin
from .models import Pharmacy, PharmacyHours
 
 

class PharmacyHoursInline(admin.TabularInline):
    model   = PharmacyHours
    extra   = 7         
    fields  = ['day_of_week', 'open_time', 'close_time', 'is_closed']
    ordering = ['day_of_week']
 
 
@admin.register(Pharmacy)
class PharmacyAdmin(admin.ModelAdmin):
    inlines       = [PharmacyHoursInline] 
    list_display  = ['name', 'county', 'sub_county', 'license_number',
                     'license_expiry', 'is_active', 'is_24hr']
    list_filter   = ['county', 'is_active', 'is_24hr']
    search_fields = ['name', 'license_number', 'email', 'phone']
    readonly_fields = ['created_at', 'updated_at']
 
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'email', 'phone', 'logo')
        }),
        ('Location', {
            'fields': ('address_line1', 'address_line2', 'county',
                       'sub_county', 'gps_lat', 'gps_lng', 'delivery_zones')
        }),
        ('License', {
            'fields': ('license_number', 'license_expiry')
        }),
        ('Status', {
            'fields': ('is_active', 'is_24hr', 'created_at', 'updated_at')
        }),
    )
 
 
@admin.register(PharmacyHours)
class PharmacyHoursAdmin(admin.ModelAdmin):
    list_display  = ['pharmacy', 'day_of_week', 'open_time', 'close_time', 'is_closed']
    list_filter   = ['day_of_week', 'is_closed']
    search_fields = ['pharmacy__name']
