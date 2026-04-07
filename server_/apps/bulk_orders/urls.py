from django.urls import path
from . import views

urlpatterns = [
  
    path('suppliers/',
        views.SupplierListView.as_view(),
        name='supplier-list'),

  
    path('',
        views.BulkOrderListView.as_view(),
        name='bulkorder-list'),

    path('auto-suggest/',
        views.AutoSuggestView.as_view(),
        name='bulkorder-suggest'),

    path('<uuid:po_id>/',
        views.BulkOrderDetailView.as_view(),
        name='bulkorder-detail'),

    path('<uuid:po_id>/submit/',
        views.SubmitBulkOrderView.as_view(),
        name='bulkorder-submit'),

    path('<uuid:po_id>/receive/',
        views.ReceiveBulkOrderView.as_view(),
        name='bulkorder-receive'),

    path('<uuid:po_id>/cancel/',
        views.CancelBulkOrderView.as_view(),
        name='bulkorder-cancel'),
]