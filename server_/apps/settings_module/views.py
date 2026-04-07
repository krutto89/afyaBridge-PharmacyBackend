from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .models import Pharmacy, PharmacyHours
from .serializers import PharmacySerializer, PharmacyHoursSerializer
from utils.permissions import IsManager
import utils.responses as resp


class PharmacyDetailView(APIView):
    permission_classes = [IsAuthenticated]
 
    def get_pharmacy(self, request):
        return request.user.pharmacy
 
    def get(self, request):
        pharmacy = self.get_pharmacy(request)
        if not pharmacy:
            return resp.not_found('Pharmacy not found')
        serializer = PharmacySerializer(pharmacy, context={'request': request})
        return resp.success(serializer.data)
 
    def put(self, request):
        permission = IsManager()
        if not permission.has_permission(request, self):
            return resp.forbidden()
        pharmacy = self.get_pharmacy(request)
        serializer = PharmacySerializer(
            pharmacy, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return resp.success(serializer.data, 'Pharmacy updated')
        return resp.error('Validation failed', serializer.errors)
 
 
class PharmacyLogoView(APIView):
    permission_classes = [IsAuthenticated]
 
    def patch(self, request):
        logo = request.FILES.get('logo')
        if not logo:
            return resp.error('No logo file provided')
        pharmacy = request.user.pharmacy
        pharmacy.logo = logo
        pharmacy.save()
        serializer = PharmacySerializer(pharmacy, context={'request': request})
        return resp.success({'logo_url': serializer.data['logo_url']}, 'Logo updated')
 
 
class PharmacyHoursView(APIView):
    permission_classes = [IsAuthenticated]
 
    def get(self, request):
        hours = PharmacyHours.objects.filter(pharmacy=request.user.pharmacy)
        return resp.success(PharmacyHoursSerializer(hours, many=True).data)
 
    def put(self, request):
        pharmacy = request.user.pharmacy
        hours_data = request.data.get('hours', [])
        for h in hours_data:
            PharmacyHours.objects.update_or_create(
                pharmacy=pharmacy, day_of_week=h['day_of_week'],
                defaults={'open_time': h['open_time'], 'close_time': h['close_time'],
                          'is_closed': h.get('is_closed', False)}
            )
        return resp.success(message='Hours updated')
