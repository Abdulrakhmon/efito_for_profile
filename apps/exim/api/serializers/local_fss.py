from rest_framework import serializers

from exim.models import LocalFSSApplication
from fumigation.models import CertificateOfDisinfestation


class LocalFSSApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocalFSSApplication
        fields = ['request_number', 'request_date', 'applicant_type', 'applicant_tin', 'applicant_name',
                  'applicant_region', 'applicant_address', 'applicant_phone', 'manufactured_region',
                  'manufactured_district', 'sender_region', 'sender_district', 'status', 'fumigation_number',
                  'fumigation_given_date', 'type', 'field_id', 'transport_number', 'products']

    def validate_fumigation_number(self, fumigation_number):
        if len(fumigation_number) > 0:
            try:
                CertificateOfDisinfestation.objects.get(number=fumigation_number)
            except:
                raise serializers.ValidationError(f'Ushbu {fumigation_number} raqamli zararsizlantirish akti mavjud emas.')
