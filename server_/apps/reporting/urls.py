
from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/',
        views.DashboardView.as_view(),
        name='report-dashboard'),

    path('sales/',
        views.SalesReportView.as_view(),
        name='report-sales'),

    path('deliveries/',
        views.DeliveryReportView.as_view(),
        name='report-deliveries'),

    path('prescriptions/',
        views.PrescriptionReportView.as_view(),
        name='report-prescriptions'),

    path('stock/',
        views.StockReportView.as_view(),
        name='report-stock'),
]