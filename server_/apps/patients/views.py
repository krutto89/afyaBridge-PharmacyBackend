# apps/patients/views.py
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.utils import timezone
from django.db.models import Q
import math, utils.responses as resp

from .models import Patient, PatientPrescription, RefillRequest, MpesaTransaction
from .serializers import (
    PatientPrescriptionSerializer, NearbyPharmacySerializer,
    RefillRequestSerializer, RefillSummarySerializer,
    MpesaPaySerializer, MpesaCallbackSerializer,
)
from apps.settings_module.models import Pharmacy


# ── Haversine distance formula ────────────────────────────
def haversine(lat1, lon1, lat2, lon2):
    """Returns distance in km between two GPS coordinates"""
    R = 6371
    dlat = math.radians(float(lat2) - float(lat1))
    dlon = math.radians(float(lon2) - float(lon1))
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(float(lat1))) *
         math.cos(math.radians(float(lat2))) *
         math.sin(dlon/2)**2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ── REACT/MOBILE INTEGRATION POINT ───────────────────────
# All patient endpoints use a simple patient_id passed in headers
# or a patient JWT (separate from staff JWT).
# For now we use a helper to get patient from request header.
def get_patient(request):
    patient_id = request.headers.get('X-Patient-ID')
    if not patient_id:
        return None
    try:
        return Patient.objects.get(id=patient_id, is_active=True)
    except Patient.DoesNotExist:
        return None


# ════════════════════════════════════════════════════════
# PRESCRIPTIONS & REFILLS
# ════════════════════════════════════════════════════════

# GET /api/patients/prescriptions/refillable/
class RefillablePrescriptionsView(APIView):
    """
    Returns all prescriptions the patient can currently refill.
    These are chronic/repeat prescriptions that haven't expired.
    REACT: Powers the 'My Medications' / refill dashboard screen.
    """
    permission_classes = [AllowAny]  # Replace with patient JWT later

    def get(self, request):
        patient = get_patient(request)
        if not patient:
            return resp.error('Patient ID required in X-Patient-ID header')

        refillable = PatientPrescription.objects.filter(
            patient=patient,
            refill_status='AVAILABLE',
        ).select_related('prescription').prefetch_related('prescription__items')

        return resp.success(
            PatientPrescriptionSerializer(refillable, many=True).data
        )


# POST /api/patients/prescriptions/select/
class SelectPrescriptionView(APIView):
    """
    Patient selects which prescription they want to refill.
    Creates a RefillRequest object to track the journey.
    REACT: Called when patient taps 'Refill Now' on a prescription card.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        patient = get_patient(request)
        if not patient:
            return resp.error('Patient ID required')

        pp_id = request.data.get('patient_prescription_id')
        try:
            pp = PatientPrescription.objects.get(
                id=pp_id, patient=patient, refill_status='AVAILABLE'
            )
        except PatientPrescription.DoesNotExist:
            return resp.not_found('Prescription not found or not available for refill')

        refill = RefillRequest.objects.create(
            patient=patient,
            patient_prescription=pp,
            status='PENDING'
        )
        pp.refill_status = 'PENDING'
        pp.save()

        return resp.created({
            'refill_id': str(refill.id),
            'status':    refill.status,
            'next_step': 'Select a pharmacy',
        }, 'Refill request created')


# POST /api/patients/prescriptions/pharmacy/select/
class SelectPharmacyView(APIView):
    """
    Patient selects which pharmacy will fulfill the refill.
    REACT: Called when patient taps a pharmacy on the map/list.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        patient = get_patient(request)
        if not patient:
            return resp.error('Patient ID required')

        refill_id   = request.data.get('refill_id')
        pharmacy_id = request.data.get('pharmacy_id')

        try:
            refill = RefillRequest.objects.get(id=refill_id, patient=patient)
        except RefillRequest.DoesNotExist:
            return resp.not_found('Refill request not found')

        try:
            pharmacy = Pharmacy.objects.get(id=pharmacy_id, is_active=True)
        except Pharmacy.DoesNotExist:
            return resp.not_found('Pharmacy not found')

        refill.selected_pharmacy = pharmacy
        refill.status            = 'PHARMACY_SELECTED'
        refill.save()

        return resp.success({
            'refill_id':    str(refill.id),
            'pharmacy':     pharmacy.name,
            'status':       refill.status,
            'next_step':    'Set delivery location or proceed to payment',
        }, 'Pharmacy selected')


# POST /api/patients/prescriptions/refill/
class InitiateRefillView(APIView):
    """
    Final confirmation of refill details before payment.
    Sets delivery type and calculates total_amount.
    REACT: Called when patient confirms their order summary.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        patient = get_patient(request)
        if not patient:
            return resp.error('Patient ID required')

        refill_id     = request.data.get('refill_id')
        delivery_type = request.data.get('delivery_type', 'pickup')

        try:
            refill = RefillRequest.objects.get(
                id=refill_id, patient=patient,
                status='PHARMACY_SELECTED'
            )
        except RefillRequest.DoesNotExist:
            return resp.not_found('Refill request not found or pharmacy not selected yet')

        # Calculate total from prescription items + delivery fee
        items        = refill.patient_prescription.prescription.items  # JSONField list of dicts
        items_total  = sum(
            (float(i.get('unit_price', 0)) * int(i.get('quantity', 0))) for i in items if isinstance(i, dict)
        )
        delivery_fee = 150 if delivery_type == 'home_delivery' else 0
        total        = float(items_total) + delivery_fee

        refill.delivery_type  = delivery_type
        refill.total_amount   = total
        refill.status         = 'PAYMENT_PENDING'
        refill.save()

        return resp.success({
            'refill_id':     str(refill.id),
            'items_total':   float(items_total),
            'delivery_fee':  delivery_fee,
            'total_amount':  total,
            'delivery_type': delivery_type,
            'status':        'PAYMENT_PENDING',
            'next_step':     'Proceed to payment',
        }, 'Refill confirmed — proceed to payment')


# POST /api/patients/prescriptions/refill/<refill_id>/location/
class SetDeliveryLocationView(APIView):
    """
    Sets the delivery GPS coordinates and address for home delivery.
    REACT: Called from the map screen where patient pins their location.
    """
    permission_classes = [AllowAny]

    def post(self, request, refill_id):
        patient = get_patient(request)
        if not patient:
            return resp.error('Patient ID required')

        try:
            refill = RefillRequest.objects.get(id=refill_id, patient=patient)
        except RefillRequest.DoesNotExist:
            return resp.not_found('Refill not found')

        refill.delivery_address = request.data.get('address', '')
        refill.delivery_lat     = request.data.get('lat')
        refill.delivery_lng     = request.data.get('lng')
        refill.status           = 'LOCATION_SET'
        refill.save()

        return resp.success({
            'refill_id': str(refill.id),
            'address':   refill.delivery_address,
            'status':    'LOCATION_SET',
        }, 'Delivery location saved')


# ════════════════════════════════════════════════════════
# PHARMACY SEARCH
# ════════════════════════════════════════════════════════

# GET /api/patients/pharmacies/nearby/?lat=-1.286&lng=36.817&radius=5
class NearbyPharmaciesView(APIView):
    """
    Returns pharmacies within a given radius of the patient's GPS location.
    Sorted by distance (nearest first).
    REACT: Powers the map view and nearby pharmacy list.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        lat    = request.query_params.get('lat')
        lng    = request.query_params.get('lng')
        radius = float(request.query_params.get('radius', 5))  # km

        if not lat or not lng:
            return resp.error('lat and lng query params are required')

        pharmacies = Pharmacy.objects.filter(
            is_active=True,
            gps_lat__isnull=False,
            gps_lng__isnull=False
        )

        nearby = []
        for pharmacy in pharmacies:
            dist = haversine(lat, lng, pharmacy.gps_lat, pharmacy.gps_lng)
            if dist <= radius:
                pharmacy._distance_km = round(dist, 2)
                nearby.append(pharmacy)

        # Sort by distance
        nearby.sort(key=lambda p: p._distance_km)

        return resp.success(
            NearbyPharmacySerializer(
                nearby, many=True, context={'request': request}
            ).data
        )


# GET /api/patients/pharmacies/search/?q=westlands
class PharmacySearchView(APIView):
    """
    Text search for pharmacies by name, county, or sub-county.
    REACT: Search bar on the pharmacy selection screen.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        q = request.query_params.get('q', '')
        if not q:
            return resp.error('Search query q is required')

        pharmacies = Pharmacy.objects.filter(
            is_active=True
        ).filter(
            Q(name__icontains=q) |
            Q(county__icontains=q) |
            Q(sub_county__icontains=q) |
            Q(address_line1__icontains=q)
        )

        return resp.success(
            NearbyPharmacySerializer(
                pharmacies, many=True, context={'request': request}
            ).data
        )


# GET /api/patients/pharmacies/map/
class PharmacyMapView(APIView):
    """
    Returns ALL active pharmacies with GPS coordinates for map pins.
    REACT: Feeds the Google Maps / Leaflet map with all pharmacy markers.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        pharmacies = Pharmacy.objects.filter(
            is_active=True,
            gps_lat__isnull=False,
            gps_lng__isnull=False
        ).only('id', 'name', 'gps_lat', 'gps_lng',
               'address_line1', 'phone', 'is_24hr')

        return resp.success(
            NearbyPharmacySerializer(
                pharmacies, many=True, context={'request': request}
            ).data
        )


# ════════════════════════════════════════════════════════
# ORDERS & PAYMENTS
# ════════════════════════════════════════════════════════

# GET /api/patients/orders/<refill_id>/summary/
class OrderSummaryView(APIView):
    """
    Full order summary shown to patient before they pay.
    REACT: The 'Order Summary' screen before the Pay Now button.
    """
    permission_classes = [AllowAny]

    def get(self, request, refill_id):
        patient = get_patient(request)
        if not patient:
            return resp.error('Patient ID required')

        try:
            refill = RefillRequest.objects.get(id=refill_id, patient=patient)
        except RefillRequest.DoesNotExist:
            return resp.not_found('Refill not found')

        return resp.success(
            RefillSummarySerializer(refill, context={'request': request}).data
        )


# POST /api/patients/orders/<refill_id>/pay/
class PayOrderView(APIView):
    """
    Initiates M-Pesa STK Push to patient's phone.
    REACT: Called when patient taps 'Pay KES X via M-Pesa'.
    The patient then gets a prompt on their phone to enter PIN.
    """
    permission_classes = [AllowAny]

    def post(self, request, refill_id):
        patient = get_patient(request)
        if not patient:
            return resp.error('Patient ID required')

        try:
            refill = RefillRequest.objects.get(
                id=refill_id, patient=patient, status='PAYMENT_PENDING'
            )
        except RefillRequest.DoesNotExist:
            return resp.not_found('Refill not found or not ready for payment')

        serializer = MpesaPaySerializer(data=request.data)
        if not serializer.is_valid():
            return resp.error('Validation failed', serializer.errors)

        phone  = serializer.validated_data['phone']
        amount = serializer.validated_data['amount']

        # Create a pending transaction record
        txn = MpesaTransaction.objects.create(
            refill_request=refill,
            patient=patient,
            phone=phone,
            amount=amount,
            status='PENDING'
        )

        # ── REACT/MOBILE INTEGRATION POINT ──────────────
        # In production, call the Daraja STK Push API here:
        #
        # import requests, base64
        # from datetime import datetime
        #
        # # Get OAuth token
        # consumer_key    = config('MPESA_CONSUMER_KEY')
        # consumer_secret = config('MPESA_CONSUMER_SECRET')
        # token_url = 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
        # r = requests.get(token_url, auth=(consumer_key, consumer_secret))
        # token = r.json()['access_token']
        #
        # # Build STK Push
        # timestamp   = datetime.now().strftime('%Y%m%d%H%M%S')
        # shortcode   = config('MPESA_SHORTCODE')
        # passkey     = config('MPESA_PASSKEY')
        # password    = base64.b64encode(f'{shortcode}{passkey}{timestamp}'.encode()).decode()
        # stk_url     = 'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
        # payload = {
        #     'BusinessShortCode': shortcode,
        #     'Password':          password,
        #     'Timestamp':         timestamp,
        #     'TransactionType':   'CustomerPayBillOnline',
        #     'Amount':            int(amount),
        #     'PartyA':            phone,
        #     'PartyB':            shortcode,
        #     'PhoneNumber':       phone,
        #     'CallBackURL':       'https://yourserver.com/api/patients/payments/mpesa/callback/',
        #     'AccountReference':  str(refill.id)[:8],
        #     'TransactionDesc':   'AfyaBridge Pharmacy Refill',
        # }
        # r = requests.post(stk_url, json=payload,
        #                   headers={'Authorization': f'Bearer {token}'})
        # stk_data = r.json()
        # txn.merchant_request_id = stk_data.get('MerchantRequestID', '')
        # txn.checkout_request_id = stk_data.get('CheckoutRequestID', '')
        # txn.save()
        # ────────────────────────────────────────────────

        return resp.success({
            'transaction_id':     str(txn.id),
            'refill_id':          str(refill.id),
            'amount':             float(amount),
            'phone':              phone,
            'status':             'PENDING',
            'message':            'STK Push sent to your phone. Enter M-Pesa PIN to complete.',
        }, 'Payment initiated')


# GET /api/patients/orders/<refill_id>/confirmation/
class OrderConfirmationView(APIView):
    """
    Returns order confirmation after payment succeeds.
    REACT: The 'Order Confirmed' success screen.
    """
    permission_classes = [AllowAny]

    def get(self, request, refill_id):
        patient = get_patient(request)
        if not patient:
            return resp.error('Patient ID required')

        try:
            refill = RefillRequest.objects.get(id=refill_id, patient=patient)
        except RefillRequest.DoesNotExist:
            return resp.not_found('Refill not found')

        txn = refill.transactions.filter(status='SUCCESS').first()

        return resp.success({
            'refill_id':        str(refill.id),
            'status':           refill.status,
            'pharmacy':         refill.selected_pharmacy.name if refill.selected_pharmacy else None,
            'delivery_type':    refill.delivery_type,
            'total_paid':       float(refill.total_amount),
            'mpesa_receipt':    txn.mpesa_receipt_no if txn else None,
            'paid_at':          txn.completed_at if txn else None,
        })


# POST /api/patients/payments/mpesa/callback/
class MpesaCallbackView(APIView):
    """
    Safaricom calls this URL automatically after patient enters PIN.
    This endpoint must be public (no auth) and reachable from the internet.
    REACT: No frontend involvement — this is server-to-server only.
    For local testing, use ngrok to expose localhost to Safaricom.
    """
    permission_classes = [AllowAny]
    authentication_classes = []  # No auth — called by Safaricom

    def post(self, request):
        data = request.data
        try:
            callback_data  = data['Body']['stkCallback']
            result_code    = callback_data['ResultCode']
            result_desc    = callback_data['ResultDesc']
            merchant_req   = callback_data['MerchantRequestID']
            checkout_req   = callback_data['CheckoutRequestID']

            txn = MpesaTransaction.objects.get(
                checkout_request_id=checkout_req
            )

            if result_code == 0:
                # Payment successful
                items = callback_data.get('CallbackMetadata', {}).get('Item', [])
                receipt_no = next(
                    (i['Value'] for i in items if i['Name'] == 'MpesaReceiptNumber'), ''
                )
                txn.status           = 'SUCCESS'
                txn.mpesa_receipt_no = receipt_no
                txn.result_code      = result_code
                txn.result_desc      = result_desc
                txn.completed_at     = timezone.now()
                txn.save()

                # Update refill status
                refill = txn.refill_request
                refill.status = 'PAID'
                refill.save()

                # Update patient prescription refill status
                pp = refill.patient_prescription
                pp.refill_status     = 'PROCESSING'
                pp.last_refill_date  = timezone.now().date()
                pp.save()

            else:
                # Payment failed or cancelled
                txn.status      = 'FAILED'
                txn.result_code = result_code
                txn.result_desc = result_desc
                txn.save()

        except Exception as e:
            # Always return 200 to Safaricom even on error
            # otherwise they will keep retrying
            pass

        # Safaricom expects exactly this response
        return resp.success({'ResultCode': 0, 'ResultDesc': 'Accepted'})


# GET /api/patients/payments/<transaction_id>/status/
class PaymentStatusView(APIView):
    """
    React polls this endpoint every few seconds after initiating payment
    to check if the patient has completed the M-Pesa prompt.
    REACT: Used to show a loading spinner until payment is confirmed.
    """
    permission_classes = [AllowAny]

    def get(self, request, transaction_id):
        try:
            txn = MpesaTransaction.objects.get(id=transaction_id)
        except MpesaTransaction.DoesNotExist:
            return resp.not_found('Transaction not found')

        return resp.success({
            'transaction_id':  str(txn.id),
            'status':          txn.status,
            'mpesa_receipt':   txn.mpesa_receipt_no,
            'amount':          float(txn.amount),
            'completed_at':    txn.completed_at,
        })


# GET /api/patients/meds/dashboard/
class PatientMedDashboardView(APIView):
    """
    Patient's medication dashboard — all their prescriptions,
    pending refills, recent orders in one call.
    REACT: The main home screen of the patient mobile/web app.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        patient = get_patient(request)
        if not patient:
            return resp.error('Patient ID required')

        prescriptions = PatientPrescription.objects.filter(patient=patient)
        refills       = RefillRequest.objects.filter(patient=patient)

        return resp.success({
            'patient': {
                'name':  patient.full_name,
                'phone': patient.phone,
            },
            'summary': {
                'total_prescriptions': prescriptions.count(),
                'refillable_now':      prescriptions.filter(
                                           refill_status='AVAILABLE'
                                       ).count(),
                'pending_refills':     refills.filter(
                                           status__in=['PENDING','PHARMACY_SELECTED',
                                                       'PAYMENT_PENDING','PAID']
                                       ).count(),
                'completed_refills':   refills.filter(status='DELIVERED').count(),
            },
            'active_refills': RefillRequestSerializer(
                refills.filter(
                    status__in=['PAID','PROCESSING','READY']
                ), many=True
            ).data,
            'refillable_prescriptions': PatientPrescriptionSerializer(
                prescriptions.filter(refill_status='AVAILABLE'), many=True
            ).data,
        })