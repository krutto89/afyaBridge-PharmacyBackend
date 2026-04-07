from rest_framework.views import APIView
from django.utils import timezone
from .models import BulkOrder, BulkOrderItem, Supplier
from .serializers import BulkOrderSerializer, SupplierSerializer
from apps.inventory.models import Drug
from utils.permissions import IsManager
import utils.responses as resp


class BulkOrderListView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        orders = BulkOrder.objects.filter(pharmacy=request.user.pharmacy)
        return resp.success(BulkOrderSerializer(orders, many=True).data)

    def post(self, request):
        serializer = BulkOrderSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                pharmacy   = request.user.pharmacy,
                created_by = request.user.id,   # store UUID, not model instance
            )
            return resp.created(serializer.data, 'Purchase order created')
        return resp.error('Validation failed', serializer.errors)


class BulkOrderDetailView(APIView):
    permission_classes = [IsManager]

    def get(self, request, po_id):
        try:
            po = BulkOrder.objects.get(id=po_id, pharmacy=request.user.pharmacy)
        except BulkOrder.DoesNotExist:
            return resp.not_found('Purchase order not found')
        return resp.success(BulkOrderSerializer(po).data)


class SubmitBulkOrderView(APIView):
    permission_classes = [IsManager]

    def post(self, request, po_id):
        try:
            po = BulkOrder.objects.get(id=po_id, pharmacy=request.user.pharmacy)
        except BulkOrder.DoesNotExist:
            return resp.not_found('Purchase order not found')
        if po.status != 'draft':
            return resp.error('Only draft orders can be submitted')
        po.status = 'submitted'
        po.save()
        return resp.success({'status': po.status}, 'Purchase order submitted')


class ReceiveBulkOrderView(APIView):
    permission_classes = [IsManager]

    def post(self, request, po_id):
        try:
            po = BulkOrder.objects.get(id=po_id, pharmacy=request.user.pharmacy)
        except BulkOrder.DoesNotExist:
            return resp.not_found('Purchase order not found')

        items_received = request.data.get('items_received', [])
        for item_data in items_received:
            try:
                item = BulkOrderItem.objects.get(id=item_data['item_id'], bulk_order=po)
                qty  = item_data.get('quantity_received', 0)
                item.quantity_received = qty
                item.save()
                # Update drug stock via UUID lookup
                Drug.objects.filter(id=item.drug_id).update(
                    quantity_in_stock=models_F_add(item.drug_id, qty)
                )
            except BulkOrderItem.DoesNotExist:
                continue

        po.status        = 'received'
        po.received_date = timezone.now().date()
        po.save()
        return resp.success(message='Purchase order received and stock updated')


def models_F_add(drug_id, qty):
    """Helper: increment quantity_in_stock using F() expression."""
    from django.db.models import F
    Drug.objects.filter(id=drug_id).update(quantity_in_stock=F('quantity_in_stock') + qty)


class CancelBulkOrderView(APIView):
    permission_classes = [IsManager]

    def post(self, request, po_id):
        try:
            po = BulkOrder.objects.get(id=po_id, pharmacy=request.user.pharmacy)
        except BulkOrder.DoesNotExist:
            return resp.not_found('Purchase order not found')
        if po.status not in ['draft', 'submitted']:
            return resp.error('Only draft or submitted orders can be cancelled')
        po.status = 'cancelled'
        po.save()
        return resp.success({'status': 'cancelled'}, 'Purchase order cancelled')


class AutoSuggestView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        from django.db.models import F
        drugs = Drug.objects.filter(
            pharmacy=request.user.pharmacy,
            is_active=True,
            quantity_in_stock__lte=F('reorder_level')
        ).values('id', 'drug_name', 'quantity_in_stock', 'reorder_level')
        suggestions = [
            {**d, 'suggested_qty': d['reorder_level'] * 3 - d['quantity_in_stock']}
            for d in drugs
        ]
        return resp.success(suggestions)


class SupplierListView(APIView):
    permission_classes = [IsManager]

    def get(self, request):
        suppliers = Supplier.objects.filter(is_active=True)
        return resp.success(SupplierSerializer(suppliers, many=True).data)

    def post(self, request):
        serializer = SupplierSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return resp.created(serializer.data, 'Supplier added')
        return resp.error('Validation failed', serializer.errors)
