from rest_framework.views import APIView
from django.utils import timezone
from django.db.models import F as models_F
from .models import Prescription
from .serializers import PrescriptionSerializer, DispenseSerializer
from utils.pagination import StandardPagination
import utils.responses as resp


def get_pharmacy_id(user):
    """Safely get pharmacy_id even if user is not authenticated"""
    if not user.is_authenticated:
        return None
    return str(user.pharmacy_id) if getattr(user, 'pharmacy_id', None) else None


class PrescriptionListView(APIView):
    # permission_classes = [IsPharmacist]   # ← Removed to unprotect

    def get(self, request):
        pharmacy_id = get_pharmacy_id(request.user)
        
        if not pharmacy_id:
            # For development: return all prescriptions if no pharmacy linked
            # (Remove this logic later when you add proper auth)
            rxs = Prescription.objects.all()
        else:
            rxs = Prescription.objects.filter(pharmacy_id=pharmacy_id)

        status   = request.query_params.get('status')
        priority = request.query_params.get('priority')
        q        = request.query_params.get('q')

        if status:   rxs = rxs.filter(status=status)
        if priority: rxs = rxs.filter(priority=priority)
        if q:        rxs = rxs.filter(patient_name__icontains=q)

        paginator = StandardPagination()
        page = paginator.paginate_queryset(rxs, request)
        
        return paginator.get_paginated_response(
            PrescriptionSerializer(page, many=True).data
        )


class PrescriptionDetailView(APIView):
    # permission_classes = [IsPharmacist]   # ← Removed

    def get_rx(self, rx_id, pharmacy_id):
        try:
            if pharmacy_id:
                return Prescription.objects.get(id=str(rx_id), pharmacy_id=pharmacy_id)
            else:
                return Prescription.objects.get(id=str(rx_id))  # fallback for dev
        except Prescription.DoesNotExist:
            return None

    def get(self, request, rx_id):
        pharmacy_id = get_pharmacy_id(request.user)
        rx = self.get_rx(rx_id, pharmacy_id)
        
        if not rx:
            return resp.not_found('Prescription not found')
        
        return resp.success(PrescriptionSerializer(rx).data)


class ValidatePrescriptionView(APIView):
    # permission_classes = [IsPharmacist]   # ← Removed

    def post(self, request, rx_id):
        pharmacy_id = get_pharmacy_id(request.user)
        
        try:
            if pharmacy_id:
                rx = Prescription.objects.get(id=str(rx_id), pharmacy_id=pharmacy_id)
            else:
                rx = Prescription.objects.get(id=str(rx_id))   # dev fallback
        except Prescription.DoesNotExist:
            return resp.not_found('Prescription not found')

        if rx.status != 'pending':
            return resp.error('Only pending prescriptions can be validated')

        rx.status = 'validated'
        rx.notes  = request.data.get('notes', rx.notes)
        rx.save()
        
        return resp.success({'status': rx.status}, 'Prescription validated')


class RejectPrescriptionView(APIView):
    # permission_classes = [IsPharmacist]   # ← Removed

    def post(self, request, rx_id):
        pharmacy_id = get_pharmacy_id(request.user)
        
        try:
            if pharmacy_id:
                rx = Prescription.objects.get(id=str(rx_id), pharmacy_id=pharmacy_id)
            else:
                rx = Prescription.objects.get(id=str(rx_id))
        except Prescription.DoesNotExist:
            return resp.not_found('Prescription not found')

        reason = request.data.get('reason')
        if not reason:
            return resp.error('Rejection reason is required')

        rx.status           = 'rejected'
        rx.rejection_reason = reason
        rx.save()
        
        return resp.success({'status': rx.status}, 'Prescription rejected')


class DispensePrescriptionView(APIView):
    # permission_classes = [IsPharmacist]   # ← Removed

    def post(self, request, rx_id):
        pharmacy_id = get_pharmacy_id(request.user)
        
        try:
            if pharmacy_id:
                rx = Prescription.objects.get(id=str(rx_id), pharmacy_id=pharmacy_id)
            else:
                rx = Prescription.objects.get(id=str(rx_id))
        except Prescription.DoesNotExist:
            return resp.not_found('Prescription not found')

        if rx.status != 'validated':
            return resp.error('Prescription must be validated before dispensing')

        # Step 1: Check and decrement inventory for each prescription item
        from apps.inventory.models import Drug
        insufficient_stock = []
        
        for item in rx.items:
            drug_id = item.get('drug_id')
            quantity_needed = item.get('quantity', 0)
            
            try:
                drug = Drug.objects.get(id=drug_id)
                if drug.quantity_in_stock < quantity_needed:
                    insufficient_stock.append({
                        'drug_name': drug.drug_name,
                        'available': drug.quantity_in_stock,
                        'needed': quantity_needed
                    })
            except Drug.DoesNotExist:
                insufficient_stock.append({
                    'drug_name': f'Unknown drug (ID: {drug_id})',
                    'available': 0,
                    'needed': quantity_needed
                })
        
        if insufficient_stock:
            return resp.error('Insufficient stock for the following items:', insufficient_stock)

        # Step 2: Decrement inventory quantities
        for item in rx.items:
            drug_id = item.get('drug_id')
            quantity_needed = item.get('quantity', 0)
            Drug.objects.filter(id=drug_id).update(
                quantity_in_stock=models_F('quantity_in_stock') - quantity_needed
            )

        # Step 3: Check if order already exists for this prescription
        from apps.orders.models import Order
        
        existing_order = Order.objects.filter(prescription_id=rx.id).first()
        if existing_order:
            # Use existing order details
            order = existing_order
            delivery_type = order.delivery_type
            total_amount = order.total_amount
        else:
            # Create new Order record
            from apps.orders.serializers import OrderSerializer
            
            # Calculate total amount from prescription items
            total_amount = sum(
                item.get('unit_price', 0) * item.get('quantity', 0)
                for item in rx.items
            )
            
            # Default to pickup if no order exists yet
            delivery_type = 'pickup'
            total_amount += 0  # No delivery fee for pickup
            
            order_data = {
                'prescription_id': rx.id,
                'patient_id': rx.patient_id,
                'patient_name': rx.patient_name,
                'patient_phone': rx.patient_phone,
                'patient_address': rx.patient_address,
                'delivery_type': delivery_type,
                'total_amount': total_amount,
                'status': 'ready',  # Ready for pickup
            }
            
            order_serializer = OrderSerializer(data=order_data)
            if not order_serializer.is_valid():
                return resp.error('Failed to create order', order_serializer.errors)
            
            order = order_serializer.save(pharmacy_id=pharmacy_id)

        # Step 4: Create Delivery record if home delivery and none exists
        if delivery_type == 'home_delivery':
            from apps.deliveries.models import Delivery
            
            # Check if delivery already exists for this order
            if not Delivery.objects.filter(order_id=str(order.id)).exists():
                from apps.deliveries.serializers import DeliverySerializer
                
                delivery_data = {
                    'order_id': str(order.id),
                    'dropoff_location': rx.patient_address,
                    'receiver_contact': rx.patient_phone,
                    'pickup_location': f'Pharmacy {pharmacy_id}',  # Will be updated with actual pharmacy address
                    'requirement': f'Prescription delivery for {rx.patient_name}',
                    'delivery_zone': 'Local',  # Can be enhanced with actual zones
                }
                
                delivery_serializer = DeliverySerializer(data=delivery_data)
                if delivery_serializer.is_valid():
                    delivery_serializer.save()
                # Note: If delivery creation fails, we still proceed with dispensing
                # as the order is created and can be handled manually

        # Step 5: Update prescription status
        rx.status = 'dispensed'
        rx.dispensed_by = str(request.user.id) if request.user.is_authenticated else None
        rx.dispensed_at = timezone.now()
        rx.save()
        
        return resp.success({
            'status': rx.status,
            'order_id': order.id,
            'order_number': order.order_number,
            'delivery_type': delivery_type,
            'total_amount': total_amount
        }, 'Prescription dispensed successfully')