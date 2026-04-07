from rest_framework.views import APIView
from django.utils import timezone
from .models import Delivery
from .serializers import DeliverySerializer
from utils.permissions import IsPharmacist, IsPharmacistOrDelivery
from utils.helpers import get_pharmacy_id
import utils.responses as resp


class DeliveryListView(APIView):
    permission_classes = [IsPharmacistOrDelivery]

    def get(self, request):
        if not request.user.is_authenticated:
            return resp.error('Authentication required')

        if getattr(request.user, 'role', None) == 'rider':
            deliveries = Delivery.objects.filter(rider_id=str(request.user.id))
        else:
            pharmacy_id = get_pharmacy_id(request.user)
            if not pharmacy_id:
                return resp.error('Your account is not linked to a pharmacy')
            from apps.orders.models import Order
            order_ids = list(
                Order.objects.filter(pharmacy_id=pharmacy_id).values_list('id', flat=True)
            )
            deliveries = Delivery.objects.filter(order_id__in=[str(i) for i in order_ids])

        status_filter = request.query_params.get('status')
        if status_filter:
            deliveries = deliveries.filter(status=status_filter)

        return resp.success(DeliverySerializer(deliveries, many=True).data)

    def post(self, request):
        serializer = DeliverySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return resp.created(serializer.data, 'Delivery created')
        return resp.error('Validation failed', serializer.errors)


class AssignDeliveryView(APIView):
    permission_classes = [IsPharmacist]

    def post(self, request, delivery_id):
        try:
            delivery = Delivery.objects.get(id=delivery_id)
        except Delivery.DoesNotExist:
            return resp.not_found('Delivery not found')

        rider_id = request.data.get('rider_id')
        from apps.authentication.models import PharmacyUser
        try:
            PharmacyUser.objects.get(id=rider_id, role='rider')
        except PharmacyUser.DoesNotExist:
            return resp.not_found('Rider not found')

        delivery.rider_id = rider_id
        delivery.status   = 'assigned'
        delivery.save()
        return resp.success(DeliverySerializer(delivery).data, 'Rider assigned')


class DeliveryStatusView(APIView):
    permission_classes = [IsPharmacistOrDelivery]

    def patch(self, request, delivery_id):
        try:
            delivery = Delivery.objects.get(id=delivery_id)
        except Delivery.DoesNotExist:
            return resp.not_found('Delivery not found')

        new_status = request.data.get('status')
        if new_status:
            delivery.status = new_status
        if new_status == 'picked_up':
            delivery.pickup_time = timezone.now()
        if 'pickup_lat' in request.data:
            delivery.pickup_lat = request.data['pickup_lat']
        if 'pickup_lng' in request.data:
            delivery.pickup_lng = request.data['pickup_lng']
        delivery.save()
        return resp.success(DeliverySerializer(delivery).data, 'Status updated')


class ConfirmDeliveryView(APIView):
    permission_classes = [IsPharmacistOrDelivery]

    def post(self, request, delivery_id):
        try:
            delivery = Delivery.objects.get(id=delivery_id)
        except Delivery.DoesNotExist:
            return resp.not_found('Delivery not found')

        otp = request.data.get('otp_code')
        if otp != delivery.otp_code:
            return resp.error('Invalid OTP code')

        delivery.status       = 'delivered'
        delivery.delivered_at = timezone.now()
        delivery.save()

        from apps.orders.models import Order
        Order.objects.filter(id=delivery.order_id).update(status='delivered')

        return resp.success(message='Delivery confirmed')


class AvailableRidersView(APIView):
    permission_classes = [IsPharmacist]

    def get(self, request):
        from apps.authentication.models import PharmacyUser
        riders = PharmacyUser.objects.filter(role='rider', is_active=True, on_duty=True)
        from apps.authentication.serializers import UserProfileSerializer
        return resp.success(
            UserProfileSerializer(riders, many=True, context={'request': request}).data
        )
