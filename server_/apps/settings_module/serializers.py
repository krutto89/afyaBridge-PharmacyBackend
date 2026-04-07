from rest_framework import serializers
from .models import Pharmacy, PharmacyHours


class PharmacyHoursSerializer(serializers.ModelSerializer):
    class Meta:
        model  = PharmacyHours
        fields = ['id', 'day_of_week', 'open_time', 'close_time', 'is_closed']


class PharmacySerializer(serializers.ModelSerializer):
    hours    = PharmacyHoursSerializer(many=True, read_only=True)
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model  = Pharmacy
        fields = '__all__'

    def get_logo_url(self, obj):
        request = self.context.get('request')
        # logo is a CharField (path string), not an ImageField
        if obj.logo and request:
            return request.build_absolute_uri(f'/media/{obj.logo}')
        return None
