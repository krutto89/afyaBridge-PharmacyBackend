from django.urls import path
from . import views

urlpatterns = [
    path('',
        views.DeliveryListView.as_view(),
        name='delivery-list'),

    path('<uuid:delivery_id>/assign/',
        views.AssignDeliveryView.as_view(),
        name='delivery-assign'),

    path('<uuid:delivery_id>/status/',
        views.DeliveryStatusView.as_view(),
        name='delivery-status'),

    path('<uuid:delivery_id>/confirm/',
        views.ConfirmDeliveryView.as_view(),
        name='delivery-confirm'),

    path('partners/available/',
        views.AvailableRidersView.as_view(),
        name='delivery-partners'),
]