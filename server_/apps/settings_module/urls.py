
from django.urls import path
from . import views

urlpatterns = [
    path('pharmacy/',
        views.PharmacyDetailView.as_view(),
        name='pharmacy-detail'),

    path('pharmacy/logo/',
        views.PharmacyLogoView.as_view(),
        name='pharmacy-logo'),

    path('pharmacy/hours/',
        views.PharmacyHoursView.as_view(),
        name='pharmacy-hours'),
]