
from django.urls import path
from . import views

urlpatterns = [
    path('',
        views.ReceiptCreateView.as_view(),
        name='receipt-create'),

    path('<uuid:receipt_id>/',
        views.ReceiptDetailView.as_view(),
        name='receipt-detail'),

    path('<uuid:receipt_id>/pdf/',
        views.ReceiptDownloadView.as_view(),
        name='receipt-pdf'),

    path('order/<uuid:order_id>/',
        views.ReceiptByOrderView.as_view(),
        name='receipt-by-order'),
]