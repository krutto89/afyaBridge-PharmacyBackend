from rest_framework.views import APIView
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, F
from apps.orders.models import Order
from apps.inventory.models import Drug, StockBatch
from apps.prescriptions.models import Prescription
from apps.deliveries.models import Delivery
from utils.permissions import IsPharmacist
import utils.responses as resp


def _pharmacy_order_ids(pharmacy):
    """Return a queryset of order UUIDs belonging to a pharmacy."""
    if not pharmacy:
        return Order.objects.none().values_list('id', flat=True)
    return Order.objects.filter(pharmacy_id=pharmacy.id).values_list('id', flat=True)


class DashboardView(APIView):
    permission_classes = [IsPharmacist]

    def get(self, request):
        try:
            pharmacy = getattr(request.user, 'pharmacy', None)
        except Exception:
            pharmacy = None

        if not pharmacy:
            return resp.success({
                'pending_prescriptions': 0,
                'low_stock_alerts': 0,
                'critical_stock_alerts': 0,
                'ready_for_pickup': 0,
                'active_deliveries': 0,
                'today_revenue': 0.0,
                'expiring_count': 0,
            })

        today = timezone.now().date()
        cutoff = today + timedelta(days=30)

        drugs = Drug.objects.filter(pharmacy_id=pharmacy.id, is_active=True)
        order_ids = _pharmacy_order_ids(pharmacy)

        today_revenue = Order.objects.filter(
            pharmacy_id=pharmacy.id,
            payment_status='paid',
            created_at__date=today
        ).aggregate(total=Sum('total_amount'))['total'] or 0

        data = {
            'pending_prescriptions': Prescription.objects.filter(
                pharmacy_id=pharmacy.id, status='pending').count(),
            'low_stock_alerts': drugs.filter(
                quantity_in_stock__lte=F('reorder_level')).count(),
            'critical_stock_alerts': drugs.filter(
                quantity_in_stock__lte=F('critical_level')).count(),
            'ready_for_pickup': Order.objects.filter(
                pharmacy_id=pharmacy.id, status='ready').count(),
            'active_deliveries': Delivery.objects.filter(
                order_id__in=order_ids,
                status__in=['assigned', 'picked_up', 'out_for_delivery']
            ).count(),
            'today_revenue': float(today_revenue),
            'expiring_count': StockBatch.objects.filter(
                drug_id__in=drugs.values_list('id', flat=True),
                expiry_date__lte=cutoff,
                quantity_remaining__gt=0
            ).count(),
        }
        return resp.success(data)


# ==================== Other Reporting Endpoints ====================

class SalesReportView(APIView):
    permission_classes = [IsPharmacist]

    def get(self, request):
        pharmacy = getattr(request.user, 'pharmacy', None)
        if not pharmacy:
            return resp.success({'from': None, 'to': None, 'total': 0, 'count': 0})

        from_date = request.query_params.get(
            'from', str(timezone.now().date() - timedelta(days=30)))
        to_date = request.query_params.get('to', str(timezone.now().date()))

        orders = Order.objects.filter(
            pharmacy_id=pharmacy.id,
            payment_status='paid',
            created_at__date__gte=from_date,
            created_at__date__lte=to_date
        )
        return resp.success({
            'from': from_date,
            'to': to_date,
            'total': float(orders.aggregate(t=Sum('total_amount'))['t'] or 0),
            'count': orders.count(),
        })


class DeliveryReportView(APIView):
    permission_classes = [IsPharmacist]

    def get(self, request):
        pharmacy = getattr(request.user, 'pharmacy', None)
        if not pharmacy:
            return resp.success({'total_deliveries': 0, 'delivered': 0, 'success_rate_pct': 0})

        order_ids = _pharmacy_order_ids(pharmacy)
        deliveries = Delivery.objects.filter(order_id__in=order_ids)
        total = deliveries.count()
        delivered = deliveries.filter(status='delivered').count()
        success_rate = round(delivered / total * 100, 1) if total > 0 else 0

        return resp.success({
            'total_deliveries': total,
            'delivered': delivered,
            'success_rate_pct': success_rate,
        })


class PrescriptionReportView(APIView):
    permission_classes = [IsPharmacist]

    def get(self, request):
        pharmacy = getattr(request.user, 'pharmacy', None)
        if not pharmacy:
            return resp.success({
                'from': None, 'to': None, 'total': 0, 'pending': 0,
                'validated': 0, 'dispensed': 0, 'rejected': 0
            })

        from_date = request.query_params.get(
            'from', str(timezone.now().date() - timedelta(days=30)))
        to_date = request.query_params.get('to', str(timezone.now().date()))

        rxs = Prescription.objects.filter(
            pharmacy_id=pharmacy.id,
            created_at__date__gte=from_date,
            created_at__date__lte=to_date
        )
        return resp.success({
            'from': from_date,
            'to': to_date,
            'total': rxs.count(),
            'pending': rxs.filter(status='pending').count(),
            'validated': rxs.filter(status='validated').count(),
            'dispensed': rxs.filter(status='dispensed').count(),
            'rejected': rxs.filter(status='rejected').count(),
        })


class StockReportView(APIView):
    permission_classes = [IsPharmacist]

    def get(self, request):
        pharmacy = getattr(request.user, 'pharmacy', None)
        if not pharmacy:
            return resp.success({
                'total_skus': 0,
                'total_stock_value': 0.0,
                'low_stock': 0,
                'critical': 0,
                'out_of_stock': 0,
            })

        drugs = Drug.objects.filter(pharmacy_id=pharmacy.id, is_active=True)
        return resp.success({
            'total_skus': drugs.count(),
            'total_stock_value': float(
                drugs.aggregate(
                    v=Sum(F('unit_price') * F('quantity_in_stock'))
                )['v'] or 0
            ),
            'low_stock': drugs.filter(
                quantity_in_stock__lte=F('reorder_level')).count(),
            'critical': drugs.filter(
                quantity_in_stock__lte=F('critical_level')).count(),
            'out_of_stock': drugs.filter(quantity_in_stock=0).count(),
        })