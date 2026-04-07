from rest_framework.views import APIView
from django.utils import timezone
from datetime import timedelta
from django.db.models import F
from .models import Drug, StockBatch
from .serializers import DrugSerializer, RestockSerializer
from utils.pagination import StandardPagination
from utils.helpers import get_pharmacy_id
import utils.responses as resp


class DrugListCreateView(APIView):

    def get(self, request):
        pharmacy_id = get_pharmacy_id(request.user)

        if pharmacy_id:
            drugs = Drug.objects.filter(pharmacy_id=pharmacy_id, is_active=True)
        else:
            drugs = Drug.objects.filter(is_active=True)

        category = request.query_params.get('category')
        q        = request.query_params.get('q')

        if category: drugs = drugs.filter(category=category)
        if q:        drugs = drugs.filter(drug_name__icontains=q)

        paginator = StandardPagination()
        page = paginator.paginate_queryset(drugs, request)
        return paginator.get_paginated_response(DrugSerializer(page, many=True).data)

    def post(self, request):
        pharmacy_id = get_pharmacy_id(request.user)
        if not pharmacy_id:
            return resp.error('No pharmacy linked to this account.')
        serializer = DrugSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(pharmacy_id=pharmacy_id)
            return resp.created(serializer.data, 'Drug added to inventory')
        return resp.error('Validation failed', serializer.errors)


class DrugDetailView(APIView):

    def get_object(self, drug_id, pharmacy_id):
        try:
            if pharmacy_id:
                return Drug.objects.get(id=drug_id, pharmacy_id=pharmacy_id)
            return Drug.objects.get(id=drug_id)
        except Drug.DoesNotExist:
            return None

    def get(self, request, drug_id):
        pharmacy_id = get_pharmacy_id(request.user)
        drug = self.get_object(drug_id, pharmacy_id)
        if not drug:
            return resp.not_found('Drug not found')
        return resp.success(DrugSerializer(drug).data)

    def put(self, request, drug_id):
        pharmacy_id = get_pharmacy_id(request.user)
        drug = self.get_object(drug_id, pharmacy_id)
        if not drug:
            return resp.not_found('Drug not found')
        serializer = DrugSerializer(drug, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return resp.success(serializer.data, 'Drug updated successfully')
        return resp.error('Validation failed', serializer.errors)

    def delete(self, request, drug_id):
        pharmacy_id = get_pharmacy_id(request.user)
        drug = self.get_object(drug_id, pharmacy_id)
        if not drug:
            return resp.not_found('Drug not found')
        drug.is_active = False
        drug.save()
        return resp.success(message='Drug deleted successfully')


class LowStockView(APIView):

    def get(self, request):
        pharmacy_id = get_pharmacy_id(request.user)
        if pharmacy_id:
            drugs = Drug.objects.filter(
                pharmacy_id=pharmacy_id, is_active=True,
                quantity_in_stock__lte=F('reorder_level')
            )
        else:
            drugs = Drug.objects.filter(
                is_active=True, quantity_in_stock__lte=F('reorder_level')
            )
        return resp.success(DrugSerializer(drugs, many=True).data)


class ExpiringDrugsView(APIView):

    def get(self, request):
        days   = int(request.query_params.get('days', 30))
        cutoff = timezone.now().date() + timedelta(days=days)
        pharmacy_id = get_pharmacy_id(request.user)

        batches = StockBatch.objects.filter(expiry_date__lte=cutoff, quantity_remaining__gt=0)

        data = []
        for batch in batches:
            try:
                drug = Drug.objects.get(id=batch.drug_id)
                if pharmacy_id and str(drug.pharmacy_id) != pharmacy_id:
                    continue
                data.append({
                    'drug':      drug.drug_name,
                    'batch':     batch.batch_number,
                    'expiry':    batch.expiry_date,
                    'remaining': batch.quantity_remaining,
                    'category':  drug.category,
                })
            except Drug.DoesNotExist:
                pass

        return resp.success(data)


class RestockView(APIView):

    def post(self, request, drug_id):
        pharmacy_id = get_pharmacy_id(request.user)
        try:
            if pharmacy_id:
                drug = Drug.objects.get(id=str(drug_id), pharmacy_id=pharmacy_id)
            else:
                drug = Drug.objects.get(id=str(drug_id))
        except Drug.DoesNotExist:
            return resp.not_found('Drug not found')

        serializer = RestockSerializer(data=request.data)
        if not serializer.is_valid():
            return resp.error('Validation failed', serializer.errors)

        d = serializer.validated_data
        StockBatch.objects.create(
            drug_id            = str(drug.id),
            batch_number       = d['batch_no'],
            quantity_received  = d['quantity'],
            quantity_remaining = d['quantity'],
            expiry_date        = d['expiry_date'],
            received_by        = str(request.user.id) if hasattr(request.user, 'id') else 'system',
            supplier_id        = str(d['supplier_id']) if d.get('supplier_id') else None,
        )
        drug.quantity_in_stock += d['quantity']
        drug.save()
        return resp.success({'new_stock_level': drug.quantity_in_stock}, 'Stock updated')


class InventoryDashboardView(APIView):

    def get(self, request):
        pharmacy_id = get_pharmacy_id(request.user)
        if pharmacy_id:
            drugs = Drug.objects.filter(pharmacy_id=pharmacy_id, is_active=True)
        else:
            drugs = Drug.objects.filter(is_active=True)

        cutoff30 = timezone.now().date() + timedelta(days=30)

        data = {
            'total_skus':       drugs.count(),
            'low_stock_count':  drugs.filter(quantity_in_stock__lte=F('reorder_level')).count(),
            'critical_count':   drugs.filter(quantity_in_stock__lte=F('critical_level')).count(),
            'expiring_count':   StockBatch.objects.filter(
                                    expiry_date__lte=cutoff30, quantity_remaining__gt=0
                                ).count(),
        }
        return resp.success(data)
