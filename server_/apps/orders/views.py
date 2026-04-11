import uuid
import random
import string
from rest_framework.views import APIView
from django.utils import timezone
from .models import Order, OrderItem, PDispatchedItem
from .serializers import OrderSerializer, PDispatchedItemSerializer
from utils.permissions import IsPharmacist
from utils.pagination import StandardPagination
import utils.responses as resp
from apps.inventory.models import Drug
from apps.prescriptions.models import Prescription
import json


# ====================== CORE VIEWS ======================
class OrderListView(APIView):
    permission_classes = [IsPharmacist]

    def get(self, request):
        pharmacy = getattr(request.user, 'pharmacy', None)
        if not pharmacy:
            return resp.error('Your account is not linked to a pharmacy')

        orders = Order.objects.filter(pharmacy_id=pharmacy.id).order_by('-created_at')

        status = request.query_params.get('status')
        delivery_type = request.query_params.get('delivery_type')
        priority = request.query_params.get('priority')
        q = request.query_params.get('q')

        if status: orders = orders.filter(status=status)
        if delivery_type: orders = orders.filter(delivery_type=delivery_type)
        if priority: orders = orders.filter(priority=priority)
        if q: orders = orders.filter(patient_name__icontains=q)

        paginator = StandardPagination()
        page = paginator.paginate_queryset(orders, request)
        return paginator.get_paginated_response(OrderSerializer(page, many=True).data)


class OrderDetailView(APIView):
    permission_classes = [IsPharmacist]

    def get(self, request, order_id):
        pharmacy = getattr(request.user, 'pharmacy', None)
        if not pharmacy:
            return resp.error('Your account is not linked to a pharmacy')

        try:
            order = Order.objects.get(id=str(order_id), pharmacy_id=pharmacy.id)
        except Order.DoesNotExist:
            return resp.not_found('Order not found')

        return resp.success(OrderSerializer(order).data)


class OrderStatusView(APIView):
    permission_classes = [IsPharmacist]

    def patch(self, request, order_id):
        pharmacy = getattr(request.user, 'pharmacy', None)
        if not pharmacy:
            return resp.error('Your account is not linked to a pharmacy')

        try:
            order = Order.objects.get(id=str(order_id), pharmacy_id=pharmacy.id)
        except Order.DoesNotExist:
            return resp.not_found('Order not found')

        new_status = request.data.get('status')
        valid_statuses = [s[0] for s in Order.STATUS]

        if new_status not in valid_statuses:
            return resp.error(f'Invalid status. Must be one of: {valid_statuses}')

        order.status = new_status
        if new_status == 'processing':
            order.prepared_by = str(request.user.id)
        order.save()

        return resp.success(OrderSerializer(order).data, f'Status updated to {new_status}')


class TodayOrdersView(APIView):
    permission_classes = [IsPharmacist]

    def get(self, request):
        pharmacy = getattr(request.user, 'pharmacy', None)
        if not pharmacy:
            return resp.error('Your account is not linked to a pharmacy')

        today = timezone.now().date()
        orders = Order.objects.filter(pharmacy_id=pharmacy.id, created_at__date=today)
        return resp.success({
            'count': orders.count(),
            'orders': OrderSerializer(orders, many=True).data
        })


class ReadyOrdersView(APIView):
    permission_classes = [IsPharmacist]

    def get(self, request):
        pharmacy = getattr(request.user, 'pharmacy', None)
        if not pharmacy:
            return resp.error('Your account is not linked to a pharmacy')

        orders = Order.objects.filter(pharmacy_id=pharmacy.id, status='ready')
        return resp.success(OrderSerializer(orders, many=True).data)


class AvailableRidersView(APIView):
    permission_classes = [IsPharmacist]

    def get(self, request):
        from apps.authentication.models import PharmacyUser
        riders = PharmacyUser.objects.filter(
            role='rider', is_active=True, on_duty=True
        ).values('id', 'full_name', 'phone_number', 'vehicle_type', 'plate_number')
        return resp.success(list(riders))


class CancelOrderView(APIView):
    permission_classes = [IsPharmacist]

    def post(self, request, order_id):
        pharmacy = getattr(request.user, 'pharmacy', None)
        if not pharmacy:
            return resp.error('Your account is not linked to a pharmacy')

        try:
            order = Order.objects.get(id=str(order_id), pharmacy_id=pharmacy.id)
        except Order.DoesNotExist:
            return resp.not_found('Order not found')

        if order.status in ['delivered', 'cancelled', 'dispatched']:
            return resp.error(f'Cannot cancel an order with status: {order.status}')

        order.status = 'cancelled'
        order.save()
        return resp.success({'status': 'cancelled', 'reason': request.data.get('reason', '')}, 'Order cancelled')


class PatientDispatchHistoryView(APIView):
    permission_classes = [IsPharmacist]

    def get(self, request, patient_id):
        records = PDispatchedItem.objects.filter(patient_id=str(patient_id)).order_by('-created_at')
        return resp.success(PDispatchedItemSerializer(records, many=True).data)

# ====================== PROCESSING VIEWS ======================
class DispenseOrderView(APIView):
    """Patient pickup - dispense directly"""
    permission_classes = [IsPharmacist]

    def post(self, request, order_id):
        pharmacy = getattr(request.user, 'pharmacy', None)
        if not pharmacy:
            return resp.error('Your account is not linked to a pharmacy')

        try:
            order = Order.objects.get(id=str(order_id), pharmacy_id=pharmacy.id)
        except Order.DoesNotExist:
            return resp.not_found('Order not found')

        if order.status != 'ready':
            return resp.error(f'Order must be "ready". Current: {order.status}')

        if order.delivery_type == 'home_delivery':
            return resp.error('Use /assign-rider/ for home delivery orders')

        items = self._get_order_items(order)
        if not items:
            return resp.error('No items found in this order')

        stock_errors = self._check_stock(items, pharmacy.id)
        if stock_errors:
            return resp.error('Insufficient stock', {'stock_errors': stock_errors})

        self._reduce_inventory(items, pharmacy.id, request.user.id)

        order.status = 'delivered'
        order.prepared_by = str(request.user.id)
        order.save()

        return resp.success({
            'order_id': str(order.id),
            'order_number': order.order_number,
            'status': order.status,
            'items_dispensed': len(items),
        }, f'Order dispensed to {order.patient_name}')

    def _get_order_items(self, order):
        if order.prescription_id:
            try:
                rx = Prescription.objects.get(id=order.prescription_id)
                items_data = rx.items or []
                if isinstance(items_data, str):
                    items_data = json.loads(items_data)
                if isinstance(items_data, list):
                    return items_data
            except Exception:
                pass
        return list(OrderItem.objects.filter(order_id=str(order.id)).values())

    def _check_stock(self, items, pharmacy_id):
        errors = []
        for item in items:
            drug_name = item.get('name') or item.get('drug_name')
            qty = int(item.get('quantity', 1))
            try:
                drug = Drug.objects.get(name__iexact=drug_name, pharmacy_id=pharmacy_id)
                if drug.quantity_in_stock < qty:
                    errors.append(f"{drug_name}: Need {qty}, only {drug.quantity_in_stock} left")
            except Drug.DoesNotExist:
                errors.append(f"{drug_name}: Not found in inventory")
        return errors

    def _reduce_inventory(self, items, pharmacy_id, user_id):
        for item in items:
            drug_name = item.get('name') or item.get('drug_name')
            qty = int(item.get('quantity', 1))
            try:
                drug = Drug.objects.get(name__iexact=drug_name, pharmacy_id=pharmacy_id)
                drug.quantity_in_stock -= qty
                drug.save()

                PDispatchedItem.objects.create(
                    id=str(uuid.uuid4()),
                    patient_id=str(item.get('patient_id', '')),
                    pharmacy_id=pharmacy_id,
                    dispensed_by=str(user_id),
                    drug_id=item.get('drug_id'),
                    drug_name=drug_name,
                    dosage=item.get('dosage'),
                    frequency=item.get('frequency'),
                    instructions=item.get('instructions', ''),
                )
            except Exception:
                continue


class AssignRiderAndDispatchView(APIView):
    """Home delivery - assign rider"""
    permission_classes = [IsPharmacist]

    def post(self, request, order_id):
        pharmacy = getattr(request.user, 'pharmacy', None)
        if not pharmacy:
            return resp.error('Your account is not linked to a pharmacy')

        try:
            order = Order.objects.get(id=str(order_id), pharmacy_id=pharmacy.id)
        except Order.DoesNotExist:
            return resp.not_found('Order not found')

        if order.status != 'ready':
            return resp.error(f'Order must be "ready". Current: {order.status}')

        rider_id = request.data.get('rider_id')
        if not rider_id:
            return resp.error('rider_id is required')

        from apps.authentication.models import PharmacyUser
        try:
            rider = PharmacyUser.objects.get(id=rider_id, role='rider', is_active=True)
        except PharmacyUser.DoesNotExist:
            return resp.not_found('Rider not found')

        if not getattr(rider, 'on_duty', False):
            return resp.error(f'Rider {rider.full_name} is not on duty')

        items = DispenseOrderView._get_order_items(order)
        if not items:
            return resp.error('No items found in this order')

        stock_errors = DispenseOrderView._check_stock(items, pharmacy.id)
        if stock_errors:
            return resp.error('Insufficient stock', {'stock_errors': stock_errors})

        DispenseOrderView._reduce_inventory(items, pharmacy.id, request.user.id)

        from apps.deliveries.models import Delivery
        package_number = f'PKG-{str(uuid.uuid4())[:8].upper()}'
        otp_code = ''.join(random.choices(string.digits, k=6))

        delivery = Delivery.objects.create(
            package_number=package_number,
            order_id=str(order.id),
            rider_id=rider_id,
            status='assigned',
            pickup_location=request.data.get('pickup_location', ''),
            dropoff_location=order.patient_address or '',
            receiver_contact=order.patient_phone or '',
            otp_code=otp_code,
            delivery_notes=request.data.get('delivery_notes', ''),
            charges=request.data.get('charges', 0),
        )

        order.status = 'dispatched'
        order.prepared_by = str(request.user.id)
        order.save()

        return resp.success({
            'order_id': str(order.id),
            'status': order.status,
            'rider': rider.full_name,
            'delivery_id': str(delivery.id),
            'otp_code': otp_code,
        }, f'Rider {rider.full_name} assigned')