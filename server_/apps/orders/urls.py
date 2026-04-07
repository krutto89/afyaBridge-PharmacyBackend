from django.urls import path
from . import views

urlpatterns = [
    # ── Core CRUD ─────────────────────────────────────────────────────────────
    path('',
        views.OrderListView.as_view(),
        name='order-list'),

    path('today/',
        views.TodayOrdersView.as_view(),
        name='order-today'),

    path('ready/',
        views.ReadyOrdersView.as_view(),
        name='order-ready'),

    path('riders/available/',
        views.AvailableRidersView.as_view(),
        name='available-riders'),

    path('<uuid:order_id>/',
        views.OrderDetailView.as_view(),
        name='order-detail'),

    path('<uuid:order_id>/status/',
        views.OrderStatusView.as_view(),
        name='order-status'),

    path('<uuid:order_id>/cancel/',
        views.CancelOrderView.as_view(),
        name='order-cancel'),

    # ── Scenario 1: Patient walks in (pickup) ─────────────────────────────────
    # POST /api/orders/{id}/dispense/
    # Reduces inventory + creates p_dispatched + marks order delivered
    path('<uuid:order_id>/dispense/',
        views.DispenseOrderView.as_view(),
        name='order-dispense'),

    # ── Scenario 2: Home delivery ─────────────────────────────────────────────
    # POST /api/orders/{id}/assign-rider/
    # Body: { rider_id, pickup_location, delivery_notes, charges }
    # Reduces inventory + creates p_dispatched + creates delivery + marks dispatched
    path('<uuid:order_id>/assign-rider/',
        views.AssignRiderAndDispatchView.as_view(),
        name='order-assign-rider'),

    # ── Patient medication history ────────────────────────────────────────────
    # GET /api/orders/patient/{patient_id}/history/
    path('patient/<uuid:patient_id>/history/',
        views.PatientDispatchHistoryView.as_view(),
        name='patient-dispatch-history'),
]
