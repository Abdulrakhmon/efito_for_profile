from django.conf import settings
from django.db.models import Sum
from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.views import APIView
from rest_framework.response import Response
from datetime import datetime

from administration.models import IntegrationData, Integration, User, Organization, Balance, ContractPayment, Refund
from administration.statuses import ApplicationStatuses, ApplicationTypes, IntegratedDataType
from exim.api.serializers.local_fss import LocalFSSApplicationSerializer
from exim.models import LocalFSSApplication, WrongApplication, LocalFSSApplicationStatusStep, LocalFSS
from invoice.models import InvoicePayment
from invoice.statuses import InvoiceServices


class LocalFSSApplicationAddAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    renderer_classes = JSONRenderer,
    parser_classes = JSONParser,

    def post(self, request):
        user = User.objects.get(username='admin')
        data = request.data
        request_number = data.get('request_number')
        application_status = data.get('status')
        region = data.get('sender_region')
        serializer = LocalFSSApplicationSerializer(data=data)
        local_fss_application = LocalFSSApplication.objects.filter(request_number=request_number)

        integration = Integration.objects.filter(organization_code='AssalamAgro', data_type=IntegratedDataType.LOCAL_FSS_STATUS).last()

        local_fss_application_step_status_dict = dict(request_number=request_number, request_date=data.get('request_date'), status="", description="",
                                                      sender_name=user.name_ru, sender_phone=user.phone, organization_name="Ўзбекистон Республикаси Ўсимликлар карантини ва ҳимояси агентлиги",
                                                      organization_phone="71 202 10 00", sent_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        if local_fss_application.filter(
                status__in=[ApplicationStatuses.ONE_ZERO_SIX, ApplicationStatuses.ZERO_ONE_NINE]):
            WrongApplication.objects.create(
                json={'request_number': request_number},
                exception_details="Already exist.",
                application_type=ApplicationTypes.LOCAL_FSS
            )
            return Response({
                "request_number": request_number,
                "result": 1,
                "comment": 'Already exist.'
            }, status=status.HTTP_400_BAD_REQUEST)
        else:
            if local_fss_application.filter(
                    status__in=[ApplicationStatuses.ZERO_ZERO_SEVEN, ApplicationStatuses.ZERO_ONE_ZERO]):
                local_fss_application = local_fss_application.first()

                serializer = LocalFSSApplicationSerializer(local_fss_application, data=data)
                if serializer.is_valid():
                    serializer.save()
                    LocalFSSApplicationStatusStep.objects.create(
                        application=local_fss_application,
                        status=application_status,
                        description=str(ApplicationStatuses.CHOICES[application_status - 1][1]),
                        sender_name=data.get('applicant_name'),
                        sender_phone=data.get('applicant_phone'),
                        sent_data=data,
                    )
                    local_fss_application.is_active = True
                    local_fss_application.is_paid = True
                    local_fss_application.save()

                    local_fss_application_step_status_dict['description'] = str(ApplicationStatuses.CHOICES[application_status - 1][1])
                    local_fss_application_step_status_dict['status'] = int(application_status)
                    IntegrationData.objects.create(
                        integration=integration,
                        data=local_fss_application_step_status_dict
                    )
                    return Response({
                        "request_number": request_number,
                        "result": 1,
                        "comment": 'Successfully accepted.'
                    }, status=status.HTTP_202_ACCEPTED)
                else:
                    WrongApplication.objects.create(
                        json={'request_number': request_number},
                        exception_details=str(serializer.errors),
                        application_type=ApplicationTypes.LOCAL_FSS
                    )
                    return Response({
                        "request_number": request_number,
                        "result": 0,
                        "comment": str(serializer.errors)
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                if serializer.is_valid():
                    try:
                        local_fss_application = serializer.save()
                        LocalFSSApplicationStatusStep.objects.create(
                            application=local_fss_application,
                            status=ApplicationStatuses.ONE_ZERO_ZERO,
                            description=str(ApplicationStatuses.CHOICES[ApplicationStatuses.ONE_ZERO_ZERO - 1][1]),
                            sender_name=data.get('applicant_name'),
                            sender_phone=data.get('applicant_phone'),
                            sent_data=data,
                        )

                        if current_balance < settings.ONE_BASIC_ESTIMATE / 10:
                            local_fss_application_step_status_dict['description'] = f'Sizning hisobingizda mablag` yetarli emas (Mablag`: {current_balance} so`m). Iltimos, avval hisobingizni {float(settings.ONE_BASIC_ESTIMATE / 10) - float(current_balance)} so`mga to`ldiring va qayta yuboring. У вас недостаточно денег на балансе (Балансе: {current_balance} сум). Пожалуйста, пополните баланс и отправьте повторно.'
                            local_fss_application_step_status_dict['status'] = ApplicationStatuses.ZERO_ZERO_SEVEN
                            IntegrationData.objects.create(
                                integration=integration,
                                data=local_fss_application_step_status_dict
                            )
                            LocalFSSApplicationStatusStep.objects.create(
                                application=local_fss_application,
                                status=ApplicationStatuses.ZERO_ZERO_SEVEN,
                                description=local_fss_application_step_status_dict['description'],
                                sender=user,
                            )
                            local_fss_application.status = ApplicationStatuses.ZERO_ZERO_SEVEN
                            local_fss_application.is_active = False
                            local_fss_application.save()
                        else:
                            local_fss_application.is_paid = True
                            local_fss_application.save()

                        return Response({
                            "request_number": request_number,
                            "result": 1,
                            "comment": 'Successfully created.'
                        }, status=status.HTTP_201_CREATED)
                    except Exception as e:
                        WrongApplication.objects.create(
                            json={'request_number': request_number},
                            exception_details=str(e),
                            application_type=ApplicationTypes.LOCAL_FSS
                        )
                        return Response({
                            "request_number": request_number,
                            "result": 0,
                            "comment": str(e)
                        }, status=status.HTTP_400_BAD_REQUEST)
                else:
                    WrongApplication.objects.create(
                        json={'request_number': request_number},
                        exception_details=str(serializer.errors),
                        application_type=ApplicationTypes.LOCAL_FSS
                    )
                    return Response({
                        "request_number": request_number,
                        "result": 0,
                        "comment": str(serializer.errors)
                    }, status=status.HTTP_400_BAD_REQUEST)
