from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
 

from django.contrib import admin
 
admin.site.site_header  = 'AfyaBridge Pharmacy Admin'
admin.site.site_title   = 'AfyaBridge'
admin.site.index_title  = 'Pharmacy Management Dashboard'



urlpatterns = [
    path('admin/',          admin.site.urls),
 
    
    path('api/auth/',       include('apps.authentication.urls')),
 
    path('api/settings/',   include('apps.settings_module.urls')),
 
    path('api/prescriptions/', include('apps.prescriptions.urls')),
    path('api/inventory/',     include('apps.inventory.urls')),
    path('api/orders/',        include('apps.orders.urls')),
    path('api/bulk-orders/',   include('apps.bulk_orders.urls')),
    path('api/deliveries/',    include('apps.deliveries.urls')),
    path('api/reporting/',     include('apps.reporting.urls')),
    path('api/receipts/',      include('apps.receipts.urls')),
 
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
 

