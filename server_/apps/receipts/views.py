from rest_framework.views import APIView
from django.http import FileResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import os
from django.conf import settings
from .models import Receipt
from .serializers import ReceiptSerializer
from apps.orders.models import Order
from utils.permissions import IsPharmacist
import utils.responses as resp


def generate_pdf(receipt):
    """Generate a PDF receipt. Uses correct column names: subtotal, discount, total."""
    filename = f'receipt_{str(receipt.id)[:8]}.pdf'
    filepath = os.path.join(settings.MEDIA_ROOT, 'receipts', filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4

    c.setFont('Helvetica-Bold', 18)
    c.drawString(50, height - 60, 'AfyaBridge Pharmacy')
    c.setFont('Helvetica', 12)
    c.drawString(50, height - 80,  f'Receipt #{str(receipt.id)[:8].upper()}')
    c.drawString(50, height - 100, f'Date: {receipt.created_at.strftime("%d %b %Y %H:%M")}')

    # Patient info via order lookup
    try:
        order = Order.objects.get(id=receipt.order_id)
        c.drawString(50, height - 140, f'Patient: {order.patient_name}')
    except Order.DoesNotExist:
        c.drawString(50, height - 140, f'Order: {str(receipt.order_id)[:8].upper()}')

    c.drawString(50, height - 160, f'Payment: {receipt.get_payment_method_display()}')
    if receipt.mpesa_ref:
        c.drawString(50, height - 180, f'M-Pesa Ref: {receipt.mpesa_ref}')

    y = height - 220
    c.line(50, y + 10, width - 50, y + 10)
    c.drawString(50, y,      f'Subtotal: KES {receipt.subtotal}')
    c.drawString(50, y - 20, f'Discount: KES {receipt.discount}')
    c.setFont('Helvetica-Bold', 13)
    c.drawString(50, y - 45, f'TOTAL:    KES {receipt.total}')
    c.line(50, y - 55, width - 50, y - 55)

    c.setFont('Helvetica', 10)
    c.drawString(50, 60, 'Thank you for choosing AfyaBridge Pharmacy')
    c.drawString(50, 45, 'Keep this receipt for your records')
    c.save()
    return filepath, filename


class ReceiptCreateView(APIView):
    permission_classes = [IsPharmacist]

    def post(self, request):
        order_id = request.data.get('order_id')
        try:
            order = Order.objects.get(id=order_id, pharmacy=request.user.pharmacy)
        except Order.DoesNotExist:
            return resp.not_found('Order not found')

        if Receipt.objects.filter(order_id=order_id).exists():
            return resp.error('Receipt already exists for this order')

        receipt = Receipt.objects.create(
            order_id       = order.id,
            dispensed_by   = request.user.id,
            subtotal       = order.total_amount,
            total          = order.total_amount,
            payment_method = order.payment_method or 'cash',
            mpesa_ref      = order.mpesa_ref,
        )
        filepath, filename = generate_pdf(receipt)
        receipt.pdf_path = f'receipts/{filename}'
        receipt.save()
        return resp.created(ReceiptSerializer(receipt).data, 'Receipt generated')


class ReceiptDetailView(APIView):
    permission_classes = [IsPharmacist]

    def get(self, request, receipt_id):
        try:
            receipt = Receipt.objects.get(id=receipt_id)
        except Receipt.DoesNotExist:
            return resp.not_found('Receipt not found')
        return resp.success(ReceiptSerializer(receipt).data)


class ReceiptByOrderView(APIView):
    permission_classes = [IsPharmacist]

    def get(self, request, order_id):
        try:
            receipt = Receipt.objects.get(order_id=order_id)
        except Receipt.DoesNotExist:
            return resp.not_found('No receipt found for this order')
        return resp.success(ReceiptSerializer(receipt).data)


class ReceiptDownloadView(APIView):
    permission_classes = [IsPharmacist]

    def get(self, request, receipt_id):
        try:
            receipt = Receipt.objects.get(id=receipt_id)
        except Receipt.DoesNotExist:
            return resp.not_found('Receipt not found')
        filepath = os.path.join(settings.MEDIA_ROOT, receipt.pdf_path)
        if not os.path.exists(filepath):
            return resp.error('PDF file not found — try reprinting')
        return FileResponse(
            open(filepath, 'rb'), content_type='application/pdf',
            as_attachment=True, filename=os.path.basename(filepath)
        )
