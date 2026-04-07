import uuid
import random
import string
from rest_framework.views import APIView
from django.utils import timezone
from .models import Order, OrderItem, PDispatchedItem
from .serializers import OrderSerializer, PDispatchedItemSerializer
from utils.permissions import IsPharmacist
from utils.pagination import StandardPagination
from utils.helpers import get_pharmacy_id
import utils.responses as resp


class OrderListView(APIView):
    permission_classes = [IsPharmacist]

    def get(self, request):
        pharmacy_id = get_pharmacy_id(request.user)
        if not pharmacy_id:
            return resp.error('Your account is not linked to a pharmacy')

        orders = Order.objects.filter(pharmacy_id=pharmacy_id)

        status_filter = request.query_params.get('status')
        priority      = request.query_params.get('priority')
        q             = request.query_params.get('q')

        if status_filter: orders = orders.filter(status=status_filter)
        if priority:      orders = orders.filter(priority=priority)
        if q:             orders = orders.filter(patient_name__icontains=q)

        paginator = StandardPagination()
        page = paginator.paginate_queryset(orders, request)
        return paginator.get_paginated_response(OrderSerializer(page, many=True).data)

    def post(self, request):
        pharmacy_id = get_pharmacy_id(request.user)
        if not pharmacy_id:
            return resp.error('Your account is not linked to a pharmacy')
        serializer = OrderSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(pharmacy_id=pharmacy_id)
            return resp.created(serializer.data, 'Order created')
        return resp.error('Validation failed', serializer.errors)


class OrderDetailView(APIView):
    permission_classes = [IsPharmacist]

    def get(self, request, order_id):
        pharmacy_id = get_pharmacy_id(request.user)
        if not pharmacy_id:
            return resp.error('Your account is not linked to a pharmacy')
        try:
            order = Order.objects.get(id=str(order_id), pharmacy_id=pharmacy_id)
        except Order.DoesNotExist:
            return resp.not_found('Order not found')
        return resp.success(OrderSerializer(order).data)


class OrderStatusView(APIView):
    permission_classes = [IsPharmacist]

    def patch(self, request, order_id):
        pharmacy_id = get_pharmacy_id(request.user)
        if not pharmacy_id:
            return resp.error('Your account is not linked to a pharmacy')
        try:
            order = Order.objects.get(id=str(order_id), pharmacy_id=pharmacy_id)
        except Order.DoesNotExist:
            return resp.not_found('Order not found')

        new_status = request.data.get('status')
        valid = [s[0] for s in Order.STATUS]
        if new_status not in valid:
            return resp.error(f'Invalid status. Must be one of: {valid}')

        order.status = new_status
        if new_status == 'processing':
            order.prepared_by = str(request.user.id)
        order.save()
        return resp.success(OrderSerializer(order).data, 'Order status updated')


class DispenseOrderView(APIView):
    """Scenario 1: Patient pickup — dispense directly, reduce inventory, log p_dispatched."""
    permission_classes = [IsPharmacist]

    def post(self, request, order_id):
        pharmacy_id = get_pharmacy_id(request.user)
        if not pharmacy_id:
            return resp.error('Your account is not linked to a pharmacy')

        try:
            order = Order.objects.get(id=str(order_id), pharmacy_id=pharmacy_id)
        except Order.DoesNotExist:
            return resp.not_found('Order not found')

        if order.status != 'ready':
            return resp.error(f'Order must be "ready" to dispense. Current status: {order.status}')

        if order.delivery_type == 'home_delivery':
            return resp.error('This order requires home delivery. Use the Assign Rider endpoint instead.')

        items = OrderItem.objects.filter(order_id=str(order.id))
        if not items.exists():
            return resp.error('This order has no items. Add items before dispensing.')

        from apps.inventory.models import Drug

        stock_errors = []
        for item in items:
            try:
                drug = Drug.objects.get(id=item.drug_id, pharmacy_id=pharmacy_id)
                if drug.quantity_in_stock < item.quantity:
                    stock_errors.append(f'{item.drug_name}: need {item.quantity}, only {drug.quantity_in_stock} in stock')
            except Drug.DoesNotExist:
                stock_errors.append(f'{item.drug_name}: not found in inventory')

        if stock_errors:
            return resp.error('Insufficient stock', {'stock_errors': stock_errors})

        dispatched_records = []
        for item in items:
            drug = Drug.objects.get(id=item.drug_id, pharmacy_id=pharmacy_id)
            drug.quantity_in_stock -= item.quantity
            drug.save()

            record = PDispatchedItem.objects.create(
                id              = str(uuid.uuid4()),
                patient_id      = str(order.patient_id) if order.patient_id else '',
                prescription_id = str(order.prescription_id) if order.prescription_id else None,
                pharmacy_id     = pharmacy_id,
                prescribed_by   = None,
                dispensed_by    = str(request.user.id),
                drug_id         = item.drug_id,
                drug_name       = item.drug_name,
                dosage          = item.dosage,
                frequency       = item.frequency,
                instructions    = request.data.get('instructions', ''),
            )
            dispatched_records.append(record)

        order.status      = 'delivered'
        order.prepared_by = str(request.user.id)
        order.save()

        return resp.success({
            'order_id':           str(order.id),
            'order_number':       order.order_number,
            'patient_name':       order.patient_name,
            'status':             order.status,
            'items_dispensed':    len(dispatched_records),
            'dispatched_records': PDispatchedItemSerializer(dispatched_records, many=True).data,
        }, f'Order dispensed successfully to {order.patient_name}')


class AssignRiderAndDispatchView(APIView):
    """Scenario 2: Home delivery — assign rider, reduce inventory, log p_dispatched, create delivery."""
    permission_classes = [IsPharmacist]

    def post(self, request, order_id):
        pharmacy_id = get_pharmacy_id(request.user)
        if not pharmacy_id:
            return resp.error('Your account is not linked to a pharmacy')

        try:
            order = Order.objects.get(id=str(order_id), pharmacy_id=pharmacy_id)
        except Order.DoesNotExist:
            return resp.not_found('Order not found')

        if order.status != 'ready':
            return resp.error(f'Order must be "ready" before assigning a rider. Current status: {order.status}')

        rider_id = request.data.get('rider_id')
        if not rider_id:
            return resp.error('rider_id is required')

        from apps.authentication.models import PharmacyUser
        try:
            rider = PharmacyUser.objects.get(id=rider_id, role='rider', is_active=True)
        except PharmacyUser.DoesNotExist:
            return resp.not_found('Rider not found or not active')

        if not rider.on_duty:
            return resp.error(f'Rider {rider.full_name} is not on duty. Select an on-duty rider.')

        items = OrderItem.objects.filter(order_id=str(order.id))
        if not items.exists():
            return resp.error('This order has no items.')

        from apps.inventory.models import Drug

        stock_errors = []
        for item in items:
            try:
                drug = Drug.objects.get(id=item.drug_id, pharmacy_id=pharmacy_id)
                if drug.quantity_in_stock < item.quantity:
                    stock_errors.append(f'{item.drug_name}: need {item.quantity}, only {drug.quantity_in_stock} in stock')
            except Drug.DoesNotExist:
                stock_errors.append(f'{item.drug_name}: not found in inventory')

        if stock_errors:
            return resp.error('Insufficient stock', {'stock_errors': stock_errors})

        for item in items:
            drug = Drug.objects.get(id=item.drug_id, pharmacy_id=pharmacy_id)
            drug.quantity_in_stock -= item.quantity
            drug.save()

            PDispatchedItem.objects.create(
                id              = str(uuid.uuid4()),
                patient_id      = str(order.patient_id) if order.patient_id else '',
                prescription_id = str(order.prescription_id) if order.prescription_id else None,
                pharmacy_id     = pharmacy_id,
                dispensed_by    = str(request.user.id),
                drug_id         = item.drug_id,
                drug_name       = item.drug_name,
                dosage          = item.dosage,
                frequency       = item.frequency,
            )

        from apps.deliveries.models import Delivery
        package_number = f'PKG-{str(uuid.uuid4())[:8].upper()}'
        otp_code       = ''.join(random.choices(string.digits, k=6))

        delivery = Delivery.objects.create(
            package_number          = package_number,
            order_id                = str(order.id),
            rider_id                = rider_id,
            status                  = 'assigned',
            pickup_location         = request.data.get('pickup_location', f'Pharmacy: {pharmacy_id}'),
            pickup_contact          = request.data.get('pickup_contact', ''),
            dropoff_location        = order.patient_address or '',
            receiver_contact        = order.patient_phone or '',
            otp_code                = otp_code,
            delivery_notes          = request.data.get('delivery_notes', ''),
            estimated_delivery_time = request.data.get('estimated_delivery_time', ''),
            charges                 = request.data.get('charges', 0),
        )

        order.status      = 'dispatched'
        order.prepared_by = str(request.user.id)
        order.save()

        return resp.success({
            'order_id':       str(order.id),
            'order_number':   order.order_number,
            'patient_name':   order.patient_name,
            'status':         order.status,
            'rider':          rider.full_name,
            'delivery_id':    str(delivery.id),
            'package_number': package_number,
            'otp_code':       otp_code,
        }, f'Order dispatched. Rider {rider.full_name} assigned.')


class AvailableRidersView(APIView):
    permission_classes = [IsPharmacist]

    def get(self, request):
        from apps.authentication.models import PharmacyUser
        riders = PharmacyUser.objects.filter(
            role='rider', is_active=True, on_duty=True,
        ).values('id', 'full_name', 'phone_number', 'vehicle_type', 'plate_number')
        return resp.success(list(riders))


class TodayOrdersView(APIView):
    permission_classes = [IsPharmacist]

    def get(self, request):
        pharmacy_id = get_pharmacy_id(request.user)
        if not pharmacy_id:
            return resp.error('Your account is not linked to a pharmacy')
        today  = timezone.now().date()
        orders = Order.objects.filter(pharmacy_id=pharmacy_id, created_at__date=today)
        return resp.success({'count': orders.count(), 'orders': OrderSerializer(orders, many=True).data})


class ReadyOrdersView(APIView):
    permission_classes = [IsPharmacist]

    def get(self, request):
        pharmacy_id = get_pharmacy_id(request.user)
        if not pharmacy_id:
            return resp.error('Your account is not linked to a pharmacy')
        orders = Order.objects.filter(pharmacy_id=pharmacy_id, status='ready')
        return resp.success(OrderSerializer(orders, many=True).data)


class CancelOrderView(APIView):
    permission_classes = [IsPharmacist]

    def post(self, request, order_id):
        pharmacy_id = get_pharmacy_id(request.user)
        if not pharmacy_id:
            return resp.error('Your account is not linked to a pharmacy')
        try:
            order = Order.objects.get(id=str(order_id), pharmacy_id=pharmacy_id)
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
