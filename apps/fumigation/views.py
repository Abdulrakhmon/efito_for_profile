import time
from datetime import date, datetime, timedelta
from decimal import Decimal

import xlwt
from django.db.models import Q, Sum
from django.contrib import messages
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.generic import TemplateView, View

from administration.models import Region, District, Country, Unit, User, Organization, Balance, ContractPayment, Refund
from administration.statuses import Languages, ImpExpLocChoices, DisinfestationType, BioIndicatorType, UserStatuses

from fumigation.models import FumigationFormula, CertificateOfDisinfestation, DisinfectedObject, \
    DisinfectedBuildingType, FumigationChamber, FumigationDeclaration, FumigationInsecticide, InsecticideExchange, \
    InsecticidesMonthlyRemainder, OrganizationActivityType
from invoice.models import InvoicePayment
from invoice.statuses import InvoiceServices


class CertificateOfDisinfestationList(TemplateView):
    template_name = 'fumigation/certificate_of_disinfestation/list.html'

    def get(self, request, *args, **kwargs):
        regions = Region.objects.filter(pk__lt=15)
        user = request.user
        certificates_of_disinfestation = []
        number = request.GET.get('number')
        if number:
            certificates_of_disinfestation = CertificateOfDisinfestation.objects.filter(number=number)
        else:
            if user.has_perm('fumigation.list_republic_certificate_of_disinfestation'):
                certificates_of_disinfestation = CertificateOfDisinfestation.objects.filter(is_active=True)[:50]
            elif user.has_perm('fumigation.list_region_certificate_of_disinfestation'):
                certificates_of_disinfestation = CertificateOfDisinfestation.objects.filter(region=user.point.region)[:50]
            elif user.has_perm('fumigation.list_fumigator_certificate_of_disinfestation'):
                certificates_of_disinfestation = CertificateOfDisinfestation.objects.filter(fumigator=user)[:50]

        paginator = Paginator(certificates_of_disinfestation, 20)
        page = request.GET.get('page')
        try:
            certificates_of_disinfestation = paginator.page(page)
        except PageNotAnInteger:
            certificates_of_disinfestation = paginator.page(1)
        except EmptyPage:
            certificates_of_disinfestation = paginator.page(paginator.num_pages)

        if not certificates_of_disinfestation:
            messages.warning(request, '<i class="fas fa-ban"> Hет АКТ ОБЕЗЗАРАЖИВАНИЯ</i>')
        return render(request, self.template_name, {
            'page': page,
            'certificates_of_disinfestation': certificates_of_disinfestation,
            'number': number,
            'num_pages': range(paginator.num_pages),
            'regions': regions,
        })


class AddCertificateOfDisinfestation(TemplateView):
    template_name = 'fumigation/certificate_of_disinfestation/add.html'

    def get(self, request, *args, **kwargs):
        user = request.user
        week_ago = (datetime.today() - timedelta(7)).strftime('%Y-%m-%d')
        in_three_days = (datetime.today() + timedelta(3)).strftime('%Y-%m-%d')
        disinfestation_types = DisinfestationType.CHOICES
        disinfestation_type = None
        if request.GET.get('disinfestation_type'):
            disinfestation_type = request.GET.get('disinfestation_type')
        else:
            messages.error(request, 'Что-то не так с тобой.')
            return HttpResponseRedirect(reverse('fumigation:list_certificate_of_disinfestation'))
        if user.has_perm('fumigation.add_certificate_of_disinfestation'):
            try:
                exist_certificate_of_disinfestation = CertificateOfDisinfestation.objects.get(
                    pk=request.GET.get('exist_certificate_of_disinfestation_pk'))
            except CertificateOfDisinfestation.DoesNotExist:
                exist_certificate_of_disinfestation = None
            return render(request, self.template_name, context={
                'exist_certificate_of_disinfestation': exist_certificate_of_disinfestation,
                'disinfestation_types': disinfestation_types,
                'countries': Country.objects.all(),
                'regions': Region.objects.filter(pk__lt=15),
                'districts': District.objects.filter(region=user.point.region).order_by('name_en'),
                'disinfected_objects': DisinfectedObject.objects.order_by('name'),
                'organization_activity_types': OrganizationActivityType.objects.order_by('name'),
                'disinfected_building_types': DisinfectedBuildingType.objects.order_by('name_en'),
                'fumigation_chambers': FumigationChamber.objects.filter(region=user.point.region).order_by('number'),
                'fumigation_declarations': FumigationDeclaration.objects.all(),
                'fumigation_insecticides': FumigationInsecticide.objects.all(),
                'inspectors': User.objects.filter(point__region=user.point.region, username__startswith='i').order_by(
                    'name_en'),
                'units': Unit.objects.all(),
                'languages': Languages.dictionary,
                'week_ago': week_ago,
                'in_three_days': in_three_days,
                'disinfestation_type': int(disinfestation_type),
                'formulae': FumigationFormula.objects.all()
            })
        else:
            messages.error(request, 'У вас нет разрешения.')
            return HttpResponseRedirect(reverse('fumigation:list_certificate_of_disinfestation'))

    def post(self, request, *args, **kwargs):
        post = request.POST
        user = request.user
        region = user.point.region
        organization_tin = post.get('organization_tin', '')
        this_year = int(datetime.now().strftime('%y'))
        if int(region.pk) < 10:
            first_four_digits = str(this_year) + '0' + str(region.pk)
        else:
            first_four_digits = str(this_year) + str(region.pk)
        last_certificate_of_disinfestation = CertificateOfDisinfestation.all_objects.filter(
            number__startswith=first_four_digits).order_by('number').last()
        if last_certificate_of_disinfestation:
            number = str(int(last_certificate_of_disinfestation.number) + 1)
        else:
            number = this_year * 1000000000 + int(region.pk) * 10000000 + 1

        given_date = datetime.today().strftime('%Y-%m-%d')
        language = int(post.get('language', ''))
        certificate_type = post.get('type', '')
        organization_name = post.get('organization_name', '')
        country = None
        if post.get('country_pk', ''):
            country = Country.objects.get(pk=post.get('country_pk', ''))
        district = District.objects.get(pk=post.get('district_pk', ''))
        declaration_price = FumigationDeclaration.objects.get(pk=post.get('fumigation_declaration_pk', '')).price
        inspector = User.objects.get(pk=post.get('inspector_pk', ''))
        customer = post.get('customer', '')
        disinfected_building_type = DisinfectedBuildingType.objects.get(pk=post.get('disinfected_building_type_pk', ''))
        fumigation_chamber = None
        if post.get('fumigation_chamber_pk', ''):
            fumigation_chamber = FumigationChamber.objects.get(pk=post.get('fumigation_chamber_pk', ''))
        disinfected_building_info = post.get('disinfected_building_info', '')
        disinfected_building_volume = post.get('disinfected_building_volume', '')
        disinfestation_type = post.get('disinfestation_type', '')

        beginning_of_cycle = None
        beginning_of_heat_treatment = None
        ending_of_heat_treatment = None
        ending_of_cycle = None
        temperature_in_beginning_of_cycle = None
        temperature_in_beginning_of_heat_treatment = None
        wetness_in_beginning_of_cycle = None
        wetness_in_beginning_of_heat_treatment = None
        is_duration_in_established_standard = None
        is_temperature_in_established_standard = None

        disinfection_result = post.get('disinfection_result', '') + '%'
        if language == Languages.ENGLISH:
            disinfection_result = disinfection_result + ' died'
        else:
            disinfection_result = disinfection_result + ' гибель'

        insecticide = None
        if post.get('insecticide_pk', ''):
            insecticide = FumigationInsecticide.objects.get(pk=post.get('insecticide_pk', ''))
            insecticide_dosage = float(post.get('insecticide_dosage', ''))

        if insecticide:
            if insecticide.name == 'Метилбромид':
                total_price = float(declaration_price) * float(disinfected_building_volume) * float(insecticide_dosage)
            else:
                total_price = float(declaration_price) * float(disinfected_building_volume)
            temperature = post.get('temperature', '')
            beginning_of_disinfection = post.get('beginning_of_disinfection_date', '') + ' ' + post.get(
                'beginning_of_disinfection_time', '')
            ending_of_disinfection = post.get('ending_of_disinfection_date', '') + ' ' + post.get(
                'ending_of_disinfection_time', '')
            degassing_time = post.get('degassing_time_amount', '')

            degassing_time_unit = ''
            if language == Languages.ENGLISH:
                if post.get('degassing_time_unit', '') == '1':
                    degassing_time = degassing_time + ' minutes'
                else:
                    degassing_time = degassing_time + ' hours'
            else:
                if post.get('degassing_time_unit', '') == '1':
                    degassing_time = degassing_time + ' минуты'
                else:
                    degassing_time = degassing_time + ' часа'
            if insecticide.name == 'Карбофос 50%':
                insecticide_unit = Unit.objects.get(code='999')
            else:
                insecticide_unit = Unit.objects.get(code='163')
        else:
            if int(disinfestation_type) == DisinfestationType.HEATTREATMENT:
                beginning_of_cycle = datetime.strptime(
                    (post.get('beginning_of_cycle_date', '') + ' ' + post.get('beginning_of_cycle_time', '')),
                    '%Y-%m-%d %H:%M')
                beginning_of_heat_treatment = datetime.strptime((post.get('beginning_of_heat_treatment_date',
                                                                          '') + ' ' + post.get(
                    'beginning_of_heat_treatment_time', '')), '%Y-%m-%d %H:%M')
                ending_of_heat_treatment = datetime.strptime((post.get('ending_of_heat_treatment_date',
                                                                       '') + ' ' + post.get(
                    'ending_of_heat_treatment_time', '')), '%Y-%m-%d %H:%M')
                ending_of_cycle = datetime.strptime(
                    (post.get('ending_of_cycle_date', '') + ' ' + post.get('ending_of_cycle_time', '')),
                    '%Y-%m-%d %H:%M')
                temperature_in_beginning_of_cycle = post.get('temperature_in_beginning_of_cycle', '')
                temperature_in_beginning_of_heat_treatment = post.get('temperature_in_beginning_of_heat_treatment', '')
                wetness_in_beginning_of_cycle = post.get('wetness_in_beginning_of_cycle', '')
                wetness_in_beginning_of_heat_treatment = post.get('wetness_in_beginning_of_heat_treatment', '')
                if post.get('is_duration_in_established_standard', '') == 'yes':
                    is_duration_in_established_standard = True
                else:
                    is_duration_in_established_standard = False
                if post.get('is_temperature_in_established_standard', '') == 'yes':
                    is_temperature_in_established_standard = True
                else:
                    is_temperature_in_established_standard = False
                total_minutes = (ending_of_cycle - beginning_of_cycle).total_seconds() / 60
                total_price = Decimal(total_minutes) * Decimal(declaration_price / 60)

        # start check balance
        try:
            organization = Organization.objects.get(tin=organization_tin)
        except Organization.DoesNotExist:
            organization, _ = Organization.objects.get_or_create(tin=organization_tin,
                                                                 name=organization_name)
        first_day_of_month = '2022-01-01'
        balance = Balance.objects.filter(organization=organization, month=first_day_of_month, region=region,
                                         service_type=InvoiceServices.FUMIGATION).last()
        invoices_payments = InvoicePayment.objects.confirmed().filter(invoice__applicant_tin=organization_tin,
                                                                      invoice__service_type=InvoiceServices.FUMIGATION,
                                                                      invoice__region=region,
                                                                      payment_date__gte=first_day_of_month)
        contract_payments = ContractPayment.objects.filter(organization=organization,
                                                           service_type=InvoiceServices.FUMIGATION,
                                                           region=region,
                                                           payment_date__gte=first_day_of_month)
        refunds = Refund.objects.filter(organization=organization,
                                        service_type=InvoiceServices.FUMIGATION,
                                        region=region,
                                        refunded_date__gte=first_day_of_month)

        service_amount = 0
        if balance:
            current_balance = balance.amount
        else:
            current_balance = 0

        invoice_amount = invoices_payments.aggregate(Sum('payment_amount'))['payment_amount__sum']
        if invoice_amount:
            current_balance = current_balance + invoice_amount

        contract_payment_amount = contract_payments.aggregate(Sum('payment_amount'))['payment_amount__sum']
        if contract_payment_amount:
            current_balance = current_balance + contract_payment_amount

        refund_amount = refunds.aggregate(Sum('amount'))['amount__sum']
        if refund_amount:
            current_balance = current_balance - refund_amount

        certificate_of_disinfestations = CertificateOfDisinfestation.objects.filter(organization_tin=organization_tin,
                                                                                    given_date__gte=first_day_of_month,
                                                                                    region=region)
        if certificate_of_disinfestations:
            service_amount = certificate_of_disinfestations.aggregate(Sum('total_price'))['total_price__sum']
        current_balance = float(current_balance) - float(service_amount)
        # end check balance

        total_price_30_ratio = total_price * 30 / 100
        if current_balance - total_price_30_ratio < 0 and int(certificate_type) != ImpExpLocChoices.Export:
            messages.error(request, f'Sizning hisobingizda mablag` yetarli emas (Mablag`: {current_balance} so`m). Iltimos, avval hisobingizni {total_price - current_balance} so`mga to`ldiring va qayta yuboring.')
            return redirect(request.get_full_path())
        disinfected_product = post.get('disinfected_product', '')
        disinfected_product_amount = None
        if post.get('disinfected_product_amount', ''):
            disinfected_product_amount = float(post.get('disinfected_product_amount', ''))
        disinfected_product_unit = None
        if post.get('disinfected_product_unit_pk', ''):
            disinfected_product_unit = Unit.objects.get(pk=post.get('disinfected_product_unit_pk', ''))
        if int(disinfestation_type) == DisinfestationType.WETPROCESSING:
            disinfected_building_unit = Unit.objects.get(code='055')
        else:
            disinfected_building_unit = Unit.objects.get(code='113')

        disinfected_object = DisinfectedObject.objects.get(pk=post.get('disinfected_object_pk', ''))
        organization_activity_type = OrganizationActivityType.objects.get(
            pk=post.get('organization_activity_type_pk', ''))
        # try:
        certificate_of_disinfestation = CertificateOfDisinfestation.objects.create(
            region=region,
            district=district,
            number=number,
            given_date=given_date,
            language=int(language),
            type=certificate_type,
            organization_name=organization_name,
            organization_tin=organization_tin,
            organization_activity_type=organization_activity_type,
            country=country,
            declaration_price=int(declaration_price),
            total_price=total_price,
            fumigator=user,
            inspector=inspector,
            customer=customer,
            disinfected_building_type=disinfected_building_type,
            fumigation_chamber=fumigation_chamber,
            disinfected_building_info=disinfected_building_info,
            disinfected_building_volume=disinfected_building_volume,
            disinfected_building_unit=disinfected_building_unit,
            disinfected_product=disinfected_product,
            disinfected_product_amount=disinfected_product_amount,
            disinfected_product_unit=disinfected_product_unit,
            disinfestation_type=int(disinfestation_type),
            disinfected_object=disinfected_object,
            disinfection_result=disinfection_result
        )
        if int(disinfestation_type) == DisinfestationType.HEATTREATMENT:
            certificate_of_disinfestation.beginning_of_cycle = beginning_of_cycle
            certificate_of_disinfestation.beginning_of_heat_treatment = beginning_of_heat_treatment
            certificate_of_disinfestation.ending_of_heat_treatment = ending_of_heat_treatment
            certificate_of_disinfestation.ending_of_cycle = ending_of_cycle
            certificate_of_disinfestation.temperature_in_beginning_of_cycle = temperature_in_beginning_of_cycle
            certificate_of_disinfestation.temperature_in_beginning_of_heat_treatment = temperature_in_beginning_of_heat_treatment
            certificate_of_disinfestation.wetness_in_beginning_of_cycle = wetness_in_beginning_of_cycle
            certificate_of_disinfestation.wetness_in_beginning_of_heat_treatment = wetness_in_beginning_of_heat_treatment
            certificate_of_disinfestation.is_duration_in_established_standard = is_duration_in_established_standard
            certificate_of_disinfestation.is_temperature_in_established_standard = is_temperature_in_established_standard
            certificate_of_disinfestation.save()
        else:
            certificate_of_disinfestation.insecticide = insecticide
            certificate_of_disinfestation.insecticide_dosage = insecticide_dosage
            certificate_of_disinfestation.insecticide_unit = insecticide_unit
            certificate_of_disinfestation.expended_insecticide_amount = float(insecticide_dosage) * float(
                disinfected_building_volume)
            certificate_of_disinfestation.temperature = temperature
            certificate_of_disinfestation.beginning_of_disinfection = beginning_of_disinfection
            certificate_of_disinfestation.ending_of_disinfection = ending_of_disinfection
            certificate_of_disinfestation.degassing_time = degassing_time
            certificate_of_disinfestation.save()

        messages.success(request, 'АКТ ОБЕЗЗАРАЖИВАНИЯ  успешно зарегистрировано')
        return HttpResponseRedirect(reverse('fumigation:list_certificate_of_disinfestation') + '?number=' +
                                    str(certificate_of_disinfestation.number))
        # except Exception as e:
        #     messages.error(request, str(e))
        #     return HttpResponseRedirect(reverse('fumigation:add_certificate_of_disinfestation'))


class SendInsecticideExchange(View):
    def post(self, request, *args, **kwargs):
        post = request.POST
        user = request.user
        try:
            insecticide = FumigationInsecticide.objects.get(pk=post.get('insecticide_pk', ''))
        except FumigationInsecticide.DoesNotExist:
            messages.error(request, 'Бундай дори мавжуд эмас.')
            return HttpResponseRedirect(reverse('fumigation:view_report_of_chemicals'))

        try:
            receiver_region = Region.objects.get(pk=post.get('receiver_region_pk', ''))
        except Region.DoesNotExist:
            messages.error(request, 'Бундай инспексия мавжуд эмас.')
            return HttpResponseRedirect(reverse('fumigation:view_report_of_chemicals'))

        amount = int(post.get('amount', '')) * 1000
        exchanged_date = post.get('exchanged_date', '')
        description = post.get('description', '')
        try:
            insecticide_exchange = InsecticideExchange.objects.create(
                insecticide=insecticide,
                amount=amount,
                exchanged_date=exchanged_date,
                description=description,
                receiver_region=receiver_region,
                sender_region=user.point.region,
                sender=user,
                is_active=False,
            )
            if user.point.region == receiver_region:
                insecticide_exchange.sender_region = None
                insecticide_exchange.receiver = user
                insecticide_exchange.is_active = True
                insecticide_exchange.save()
            messages.success(request, 'Муваффақиятли юборилди. Тасдиқланишини кутинг.')
            return HttpResponseRedirect(reverse('fumigation:view_report_of_chemicals'))
        except Exception as e:
            messages.error(request, str(e))
            return HttpResponseRedirect(reverse('fumigation:view_report_of_chemicals'))


class DeleteInsecticideExchange(View):
    def get(self, request, *args, **kwargs):
        user = request.user
        insecticide_exchange_pk = kwargs.get('pk')
        try:
            insecticide_exchange = InsecticideExchange.all_objects.get(pk=insecticide_exchange_pk, is_active=False,
                                                                       sender=user)
            messages.success(request, 'Успешно сделано.')
            insecticide_exchange.delete()
        except InsecticideExchange.DoesNotExist:
            messages.error(request, 'Не существует!!!')
        return HttpResponseRedirect(reverse('fumigation:view_report_of_chemicals'))


class ApproveInsecticideExchange(View):
    def get(self, request, *args, **kwargs):
        user = request.user
        insecticide_exchange_pk = kwargs.get('pk')
        try:
            insecticide_exchange = InsecticideExchange.all_objects.get(pk=insecticide_exchange_pk, is_active=False,
                                                                       receiver_region=user.point.region)
            messages.success(request, 'Успешно сделано.')
            insecticide_exchange.is_active = True
            insecticide_exchange.receiver = user
            insecticide_exchange.save()
        except InsecticideExchange.DoesNotExist:
            messages.error(request, 'Не существует!!!')
        return HttpResponseRedirect(reverse('fumigation:view_report_of_chemicals'))


class EditCertificateOfDisinfestation(TemplateView):
    template_name = 'fumigation/certificate_of_disinfestation/edit.html'

    def dispatch(self, request, *args, **kwargs):
        is_republic_manager = request.user.groups.filter(name='Republic Manager Fumigator').exists()
        if request.user.has_perm('fumigation.add_certificate_of_disinfestation') or is_republic_manager:
            try:
                changeable_time = 1440
                if is_republic_manager:
                    changeable_time = 443200  # TODO 43200
                    certificate_of_disinfestation = CertificateOfDisinfestation.objects.get(pk=kwargs.get('pk'))
                else:
                    certificate_of_disinfestation = CertificateOfDisinfestation.objects.get(pk=kwargs.get('pk'),
                                                                                            fumigator=request.user)
                added_at = (time.mktime(datetime.now().timetuple()) - time.mktime(
                    certificate_of_disinfestation.added_at.timetuple())) / 60
                if added_at < changeable_time:
                    kwargs.update({'certificate_of_disinfestation': certificate_of_disinfestation})
                    return super(EditCertificateOfDisinfestation, self).dispatch(request, *args, **kwargs)
                else:
                    messages.error(request, f'Вам нужно было отредактировать за {changeable_time / 60} часа')
                    return HttpResponseRedirect(reverse('fumigation:list_certificate_of_disinfestation'))
            except CertificateOfDisinfestation.DoesNotExist:
                messages.error(request, 'Не найдено')
                return HttpResponseRedirect(reverse('fumigation:list_certificate_of_disinfestation'))
        else:
            messages.error(request, 'У вас нет разрешения.')
            return HttpResponseRedirect(reverse('fumigation:list_certificate_of_disinfestation'))

    def get(self, request, *args, **kwargs):
        certificate_of_disinfestation = kwargs.get('certificate_of_disinfestation')
        user = request.user
        week_ago = (datetime.today() - timedelta(7)).strftime('%Y-%m-%d')
        in_three_days = (datetime.today() + timedelta(3)).strftime('%Y-%m-%d')
        fumigation_declaration = FumigationDeclaration.objects.filter(
            price=certificate_of_disinfestation.declaration_price).first()
        beginning_of_cycle_date = None
        beginning_of_cycle_time = None
        beginning_of_heat_treatment_date = None
        beginning_of_heat_treatment_time = None
        ending_of_heat_treatment_date = None
        ending_of_heat_treatment_time = None
        ending_of_cycle_date = None
        ending_of_cycle_time = None
        beginning_of_disinfection_date = None
        beginning_of_disinfection_time = None
        ending_of_disinfection_date = None
        ending_of_disinfection_time = None
        if int(certificate_of_disinfestation.disinfestation_type) == 3:
            beginning_of_cycle_date = certificate_of_disinfestation.beginning_of_cycle.strftime('%Y-%m-%d')
            beginning_of_cycle_time = certificate_of_disinfestation.beginning_of_cycle.strftime('%H:%M')
            beginning_of_heat_treatment_date = certificate_of_disinfestation.beginning_of_heat_treatment.strftime('%Y-%m-%d')
            beginning_of_heat_treatment_time = certificate_of_disinfestation.beginning_of_heat_treatment.strftime('%H:%M')
            ending_of_heat_treatment_date = certificate_of_disinfestation.ending_of_heat_treatment.strftime('%Y-%m-%d')
            ending_of_heat_treatment_time = certificate_of_disinfestation.ending_of_heat_treatment.strftime('%H:%M')
            ending_of_cycle_date = certificate_of_disinfestation.ending_of_cycle.strftime('%Y-%m-%d')
            ending_of_cycle_time = certificate_of_disinfestation.ending_of_cycle.strftime('%H:%M')
        else:
            beginning_of_disinfection_date = certificate_of_disinfestation.beginning_of_disinfection.strftime('%Y-%m-%d')
            beginning_of_disinfection_time = certificate_of_disinfestation.beginning_of_disinfection.strftime('%H:%M')
            ending_of_disinfection_date = certificate_of_disinfestation.ending_of_disinfection.strftime('%Y-%m-%d')
            ending_of_disinfection_time = certificate_of_disinfestation.ending_of_disinfection.strftime('%H:%M')
        return render(request, self.template_name, context={
            'certificate_of_disinfestation': certificate_of_disinfestation,
            'countries': Country.objects.all(),
            'regions': Region.objects.filter(pk__lt=15),
            'districts': District.objects.filter(region=user.point.region).order_by('name_en'),
            'disinfected_objects': DisinfectedObject.objects.order_by('name'),
            'disinfected_building_types': DisinfectedBuildingType.objects.order_by('name_en'),
            'organization_activity_types': OrganizationActivityType.objects.order_by('name'),
            'fumigation_chambers': FumigationChamber.objects.filter(region=user.point.region).order_by('number'),
            'fumigation_declarations': FumigationDeclaration.objects.all(),
            'fumigation_insecticides': FumigationInsecticide.objects.all(),
            'inspectors': User.objects.filter(point__region=user.point.region, username__startswith='i').order_by(
                'name_en'),
            'units': Unit.objects.all(),
            'languages': Languages.dictionary,
            'week_ago': week_ago,
            'in_three_days': in_three_days,
            'formulae': FumigationFormula.objects.all(),
            'fumigation_declaration': fumigation_declaration,
            'beginning_of_disinfection_date': beginning_of_disinfection_date,
            'beginning_of_disinfection_time': beginning_of_disinfection_time,
            'ending_of_disinfection_date': ending_of_disinfection_date,
            'ending_of_disinfection_time': ending_of_disinfection_time,
            'beginning_of_cycle_date': beginning_of_cycle_date,
            'beginning_of_cycle_time': beginning_of_cycle_time,
            'beginning_of_heat_treatment_date': beginning_of_heat_treatment_date,
            'beginning_of_heat_treatment_time': beginning_of_heat_treatment_time,
            'ending_of_heat_treatment_date': ending_of_heat_treatment_date,
            'ending_of_heat_treatment_time': ending_of_heat_treatment_time,
            'ending_of_cycle_date': ending_of_cycle_date,
            'ending_of_cycle_time': ending_of_cycle_time,
            'disinfestation_types': DisinfestationType.CHOICES,
        })

    def post(self, request, *args, **kwargs):
        certificate_of_disinfestation = kwargs.get('certificate_of_disinfestation')
        post = request.POST
        user = request.user

        language = int(post.get('language', ''))
        certificate_type = post.get('type', '')
        organization_name = post.get('organization_name', '')
        if post.get('organization_tin', '') == '' or post.get('organization_tin', '') == '0':
            organization_tin = user.tin
        else:
            organization_tin = post.get('organization_tin', '')
        country = None
        if post.get('country_pk', ''):
            country = Country.objects.get(pk=post.get('country_pk', ''))
        district = District.objects.get(pk=post.get('district_pk', ''))
        declaration_price = FumigationDeclaration.objects.get(pk=post.get('fumigation_declaration_pk', '')).price
        inspector = User.objects.get(pk=post.get('inspector_pk', ''))
        customer = post.get('customer', '')
        disinfected_building_type = DisinfectedBuildingType.objects.get(pk=post.get('disinfected_building_type_pk', ''))
        fumigation_chamber = None
        if post.get('fumigation_chamber_pk', ''):
            fumigation_chamber = FumigationChamber.objects.get(pk=post.get('fumigation_chamber_pk', ''))
        disinfected_building_info = post.get('disinfected_building_info', '')
        disinfected_building_volume = post.get('disinfected_building_volume', '')
        disinfestation_type = post.get('disinfestation_type', '')

        beginning_of_cycle = None
        beginning_of_heat_treatment = None
        ending_of_heat_treatment = None
        ending_of_cycle = None
        temperature_in_beginning_of_cycle = None
        temperature_in_beginning_of_heat_treatment = None
        wetness_in_beginning_of_cycle = None
        wetness_in_beginning_of_heat_treatment = None
        is_duration_in_established_standard = None
        is_temperature_in_established_standard = None

        disinfection_result = post.get('disinfection_result', '') + '%'
        if language == Languages.ENGLISH:
            disinfection_result = disinfection_result + ' died'
        else:
            disinfection_result = disinfection_result + ' гибель'

        insecticide = None
        if post.get('insecticide_pk', ''):
            insecticide = FumigationInsecticide.objects.get(pk=post.get('insecticide_pk', ''))
            insecticide_dosage = float(post.get('insecticide_dosage', ''))

        if insecticide:
            if insecticide.name == 'Метилбромид':
                total_price = float(declaration_price) * float(disinfected_building_volume) * float(insecticide_dosage)
            else:
                total_price = float(declaration_price) * float(disinfected_building_volume)
            temperature = post.get('temperature', '')
            beginning_of_disinfection = post.get('beginning_of_disinfection_date', '') + ' ' + post.get(
                'beginning_of_disinfection_time', '')
            ending_of_disinfection = post.get('ending_of_disinfection_date', '') + ' ' + post.get(
                'ending_of_disinfection_time', '')
            degassing_time = post.get('degassing_time_amount', '')

            degassing_time_unit = ''
            if language == Languages.ENGLISH:
                if post.get('degassing_time_unit', '') == '1':
                    degassing_time = degassing_time + ' minutes'
                else:
                    degassing_time = degassing_time + ' hours'
            else:
                if post.get('degassing_time_unit', '') == '1':
                    degassing_time = degassing_time + ' минуты'
                else:
                    degassing_time = degassing_time + ' часа'
            if insecticide.name == 'Карбофос 50%':
                insecticide_unit = Unit.objects.get(code='999')
            else:
                insecticide_unit = Unit.objects.get(code='163')
        else:
            if int(disinfestation_type) == DisinfestationType.HEATTREATMENT:
                beginning_of_cycle = datetime.strptime(
                    (post.get('beginning_of_cycle_date', '') + ' ' + post.get('beginning_of_cycle_time', '')),
                    '%Y-%m-%d %H:%M')
                beginning_of_heat_treatment = datetime.strptime((post.get('beginning_of_heat_treatment_date',
                                                                          '') + ' ' + post.get(
                    'beginning_of_heat_treatment_time', '')), '%Y-%m-%d %H:%M')
                ending_of_heat_treatment = datetime.strptime((post.get('ending_of_heat_treatment_date',
                                                                       '') + ' ' + post.get(
                    'ending_of_heat_treatment_time', '')), '%Y-%m-%d %H:%M')
                ending_of_cycle = datetime.strptime(
                    (post.get('ending_of_cycle_date', '') + ' ' + post.get('ending_of_cycle_time', '')),
                    '%Y-%m-%d %H:%M')
                temperature_in_beginning_of_cycle = post.get('temperature_in_beginning_of_cycle', '')
                temperature_in_beginning_of_heat_treatment = post.get('temperature_in_beginning_of_heat_treatment', '')
                wetness_in_beginning_of_cycle = post.get('wetness_in_beginning_of_cycle', '')
                wetness_in_beginning_of_heat_treatment = post.get('wetness_in_beginning_of_heat_treatment', '')
                if post.get('is_duration_in_established_standard', '') == 'yes':
                    is_duration_in_established_standard = True
                else:
                    is_duration_in_established_standard = False
                if post.get('is_temperature_in_established_standard', '') == 'yes':
                    is_temperature_in_established_standard = True
                else:
                    is_temperature_in_established_standard = False
                total_minutes = (ending_of_cycle - beginning_of_cycle).total_seconds() / 60
                total_price = Decimal(total_minutes) * Decimal(declaration_price / 60)

        disinfected_product = post.get('disinfected_product', '')
        disinfected_product_amount = None
        if post.get('disinfected_product_amount', ''):
            disinfected_product_amount = float(post.get('disinfected_product_amount', ''))
        disinfected_product_unit = None
        if post.get('disinfected_product_unit_pk', ''):
            disinfected_product_unit = Unit.objects.get(pk=post.get('disinfected_product_unit_pk', ''))
        if int(disinfestation_type) == DisinfestationType.WETPROCESSING:
            disinfected_building_unit = Unit.objects.get(code='055')
        else:
            disinfected_building_unit = Unit.objects.get(code='113')

        disinfected_object = DisinfectedObject.objects.get(pk=post.get('disinfected_object_pk', ''))
        organization_activity_type = OrganizationActivityType.objects.get(
            pk=post.get('organization_activity_type_pk', ''))
        # try:
        certificate_of_disinfestation.district = district
        certificate_of_disinfestation.language = int(language)
        # certificate_of_disinfestation.type = certificate_type
        certificate_of_disinfestation.organization_name = organization_name
        # certificate_of_disinfestation.organization_tin = organization_tin
        certificate_of_disinfestation.organization_activity_type = organization_activity_type
        certificate_of_disinfestation.country = country
        certificate_of_disinfestation.declaration_price = int(declaration_price)
        certificate_of_disinfestation.total_price = total_price
        certificate_of_disinfestation.inspector = inspector
        certificate_of_disinfestation.customer = customer
        certificate_of_disinfestation.disinfected_building_type = disinfected_building_type
        certificate_of_disinfestation.fumigation_chamber = fumigation_chamber
        certificate_of_disinfestation.disinfected_building_info = disinfected_building_info
        certificate_of_disinfestation.disinfected_building_volume = float(disinfected_building_volume)
        certificate_of_disinfestation.disinfected_building_unit = disinfected_building_unit
        certificate_of_disinfestation.disinfected_product = disinfected_product
        certificate_of_disinfestation.disinfected_product_amount = disinfected_product_amount
        certificate_of_disinfestation.disinfected_product_unit = disinfected_product_unit
        certificate_of_disinfestation.disinfestation_type = int(disinfestation_type)
        certificate_of_disinfestation.disinfection_result = disinfection_result
        certificate_of_disinfestation.disinfected_object = disinfected_object

        if int(disinfestation_type) == DisinfestationType.HEATTREATMENT:
            certificate_of_disinfestation.beginning_of_cycle = beginning_of_cycle
            certificate_of_disinfestation.beginning_of_heat_treatment = beginning_of_heat_treatment
            certificate_of_disinfestation.ending_of_heat_treatment = ending_of_heat_treatment
            certificate_of_disinfestation.ending_of_cycle = ending_of_cycle
            certificate_of_disinfestation.temperature_in_beginning_of_cycle = temperature_in_beginning_of_cycle
            certificate_of_disinfestation.temperature_in_beginning_of_heat_treatment = temperature_in_beginning_of_heat_treatment
            certificate_of_disinfestation.wetness_in_beginning_of_cycle = wetness_in_beginning_of_cycle
            certificate_of_disinfestation.wetness_in_beginning_of_heat_treatment = wetness_in_beginning_of_heat_treatment
            certificate_of_disinfestation.is_duration_in_established_standard = is_duration_in_established_standard
            certificate_of_disinfestation.is_temperature_in_established_standard = is_temperature_in_established_standard
        else:
            certificate_of_disinfestation.insecticide = insecticide
            certificate_of_disinfestation.insecticide_dosage = insecticide_dosage
            certificate_of_disinfestation.insecticide_unit = insecticide_unit
            certificate_of_disinfestation.expended_insecticide_amount = float(insecticide_dosage) * float(
                disinfected_building_volume)
            certificate_of_disinfestation.temperature = temperature
            certificate_of_disinfestation.beginning_of_disinfection = beginning_of_disinfection
            certificate_of_disinfestation.ending_of_disinfection = ending_of_disinfection
            certificate_of_disinfestation.degassing_time = degassing_time
        certificate_of_disinfestation.save()
        messages.success(request, 'АКТ ОБЕЗЗАРАЖИВАНИЯ  успешно зарегистрировано')
        return HttpResponseRedirect(reverse('fumigation:list_certificate_of_disinfestation') + '?number=' +
                                    str(certificate_of_disinfestation.number))
        # except Exception as e:
        #     messages.error(request, str(e))
        #     return HttpResponseRedirect(reverse('fumigation:add_certificate_of_disinfestation'))


class PrintCertificateOfDisinfestation(TemplateView):
    template_name = 'fumigation/certificate_of_disinfestation/print.html'

    def get(self, request, *args, **kwargs):
        certificate_of_disinfestation = CertificateOfDisinfestation.objects.get(number=kwargs.get('number'))
        print(certificate_of_disinfestation.insecticide_unit)
        disinfected_product_unit = ''
        word_tin = ''
        country = 'Узбекистан'
        disinfected_building_unit = ''
        disinfected_building_type = ''
        disinfestation_type = ''
        insecticide_unit = ''
        bio_indicator = ''
        print('222222222')
        print(certificate_of_disinfestation.bio_indicator)
        print(BioIndicatorType.dictionary_en[certificate_of_disinfestation.bio_indicator])
        insecticide_unit = certificate_of_disinfestation.insecticide_unit
        if certificate_of_disinfestation.language == Languages.ENGLISH:
            if certificate_of_disinfestation.disinfected_product_unit:
                disinfected_product_unit = certificate_of_disinfestation.disinfected_product_unit.name_en
            word_tin = 'TIN'
            if certificate_of_disinfestation.type == ImpExpLocChoices.Export:
                country = 'Uzbekistan / ' + certificate_of_disinfestation.country.name_en
            elif certificate_of_disinfestation.type == ImpExpLocChoices.Import:
                country = certificate_of_disinfestation.country.name_en + ' / Uzbekistan'
            disinfected_building_unit = certificate_of_disinfestation.disinfected_building_unit.name_en
            disinfected_building_type = certificate_of_disinfestation.disinfected_building_type.name_en
            disinfestation_type = DisinfestationType.dictionary_en[certificate_of_disinfestation.disinfestation_type]
            if insecticide_unit:
                insecticide_unit = insecticide_unit.name_en
            bio_indicator = BioIndicatorType.dictionary_en[certificate_of_disinfestation.bio_indicator]
        else:
            if certificate_of_disinfestation.disinfected_product_unit:
                disinfected_product_unit = certificate_of_disinfestation.disinfected_product_unit.name_ru
            word_tin = 'ИНН'
            if certificate_of_disinfestation.type == ImpExpLocChoices.Export:
                country = 'Узбекистан / ' + certificate_of_disinfestation.country.name_ru
            elif certificate_of_disinfestation.type == ImpExpLocChoices.Import:
                country = certificate_of_disinfestation.country.name_ru + ' / Узбекистан'
            disinfected_building_unit = certificate_of_disinfestation.disinfected_building_unit.name_ru
            disinfected_building_type = certificate_of_disinfestation.disinfected_building_type.name_ru
            disinfestation_type = DisinfestationType.dictionary_ru[certificate_of_disinfestation.disinfestation_type]
            if insecticide_unit:
                insecticide_unit = insecticide_unit.name_ru
            bio_indicator = BioIndicatorType.dictionary_ru[certificate_of_disinfestation.bio_indicator]

        disinfected_product_part1 = ''
        disinfected_product_part2 = ''
        disinfected_product_amount = ''
        if certificate_of_disinfestation.disinfected_product_amount:
            disinfected_product_amount = str(float(
                certificate_of_disinfestation.disinfected_product_amount)) if certificate_of_disinfestation.disinfected_product_amount > int(
                certificate_of_disinfestation.disinfected_product_amount) else str(
                int(certificate_of_disinfestation.disinfected_product_amount))
        disinfected_product_info = str(certificate_of_disinfestation.disinfected_product) + ' - ' + str(
            disinfected_product_amount) + ' ' + disinfected_product_unit
        for disinfected_product_info in disinfected_product_info.split():
            if len(disinfected_product_part1 + disinfected_product_info) < 45 and len(disinfected_product_part2) < 1:
                disinfected_product_part1 = disinfected_product_part1 + ' ' + disinfected_product_info
            else:
                disinfected_product_part2 = disinfected_product_part2 + ' ' + disinfected_product_info

        insecticide_dosage = certificate_of_disinfestation.insecticide_dosage
        if insecticide_dosage:
            insecticide_dosage = str(float(insecticide_dosage)) if insecticide_dosage > int(insecticide_dosage) else str(
                int(insecticide_dosage))

        ending_of_disinfection = certificate_of_disinfestation.ending_of_disinfection
        beginning_of_disinfection = certificate_of_disinfestation.beginning_of_disinfection
        exposition_hours = 0
        exposition_minutes = 0
        if ending_of_disinfection and beginning_of_disinfection:
            exposition_time_in_minutes = (time.mktime(ending_of_disinfection.timetuple()) - time.mktime(
                beginning_of_disinfection.timetuple())) / 60
            exposition_hours, exposition_minutes = divmod(exposition_time_in_minutes, 60)
            exposition_hours = int(exposition_hours)
            exposition_minutes = int(exposition_minutes)

        certificate_of_disinfestation_qr_code_link = f'http://efito.uz/fumigation/certificate_of_disinfestation/{certificate_of_disinfestation.number}/download'
        disinfected_building_volume = certificate_of_disinfestation.disinfected_building_volume
        if disinfected_building_volume == int(disinfected_building_volume):
            disinfected_building_volume = int(disinfected_building_volume)
        else:
            disinfected_building_volume = float(disinfected_building_volume)
        return render(request, template_name=self.template_name,
                      context={'certificate_of_disinfestation': certificate_of_disinfestation,
                               'disinfected_product_part1': disinfected_product_part1,
                               'disinfected_product_part2': disinfected_product_part2,
                               'word_tin': word_tin,
                               'country': country,
                               'disinfected_building_unit': disinfected_building_unit,
                               'disinfected_building_type': disinfected_building_type,
                               'disinfestation_type': disinfestation_type,
                               'insecticide_unit': insecticide_unit,
                               'insecticide_dosage': insecticide_dosage,
                               'exposition_hours': exposition_hours,
                               'exposition_minutes': exposition_minutes,
                               'bio_indicator': bio_indicator,
                               'certificate_of_disinfestation_qr_code_link': certificate_of_disinfestation_qr_code_link,
                               'disinfected_building_volume': disinfected_building_volume,
                               })


# class DeleteCertificateOfDisinfestation(TemplateView):
#
#     def get(self, request, *args, **kwargs):
#         user = request.user
#         certificate_of_disinfestation_pk = kwargs.get('pk')
#         try:
#             certificate_of_disinfestation = CertificateOfDisinfestation.objects.get(pk=certificate_of_disinfestation_pk, fumigator=user)
#             added_at = (time.mktime(datetime.now().timetuple()) - time.mktime(certificate_of_disinfestation.added_at.timetuple())) / 60
#             if added_at < 1440:
#                 certificate_of_disinfestation.delete()
#                 messages.success(request, f'Успешно сделано')
#             else:
#                 messages.error(request, f'Вы не можете удалить АКТ ОБЕЗЗАРАЖИВАНИЯ № {certificate_of_disinfestation.number}')
#         except CertificateOfDisinfestation.DoesNotExist:
#             messages.error(request, 'Не существует!!!')
#         return HttpResponseRedirect(reverse('fumigation:list_certificate_of_disinfestation'))


class DownloadCertificateOfDisinfestationList(View):

    def get(self, request, *args, **kwargs):

        post = request.GET
        region_pk = int(post.get('region_pk'))
        beginning_of_interval = post.get('beginning_of_interval')
        end_of_interval = post.get('end_of_interval')
        chosen_region = Region.objects.get(pk=region_pk)
        file_name = 'certificate_of_disinfestation' + '_for_' + chosen_region.name_en + '(' + beginning_of_interval + '___' + end_of_interval + ')'

        response = HttpResponse(content_type='application/ms-excel')

        # decide file name
        response['Content-Disposition'] = f'attachment; filename="{file_name}.xls"'

        # creating workbook
        wb = xlwt.Workbook(encoding='utf-8')

        # adding sheet
        ws = wb.add_sheet("sheet1")

        # Sheet header, first row
        row_num = 0

        font_style = xlwt.XFStyle()
        # headers are bold
        font_style.font.bold = True

        # column header names, you can use your own headers here
        columns = ['Hudud', 'Akt Raqami', 'Akt Sanasi', 'Tashkilot Nomi', 'INN', 'Mahsulot Nomi', 'Mahsulot Miqdori',
                   'Mahsulot Birligi', 'Hajmi', 'Birligi', 'Dek. Narxi', 'Umumiy Narxi', 'Dori', 'Dozasi',
                   'Sarflangan Dori',
                   'Обеззараженные объекты', 'Район', 'Имп_Экс_Вын', 'Фаолият тури', 'Fumigator', 'Inspecotr', 'метод']

        # write column headers in sheet
        for col_num in range(len(columns)):
            ws.write(row_num, col_num, columns[col_num], font_style)

        # Sheet body, remaining rows
        font_style = xlwt.XFStyle()

        if beginning_of_interval and end_of_interval and chosen_region:
            certificates_of_disinfestation = CertificateOfDisinfestation.objects.filter(
                given_date__gte=beginning_of_interval, given_date__lte=end_of_interval)
            if region_pk != 15:
                certificates_of_disinfestation = certificates_of_disinfestation.filter(region=chosen_region)
            for certificate_of_disinfestation in certificates_of_disinfestation:
                disinfected_product_unit = ''
                if certificate_of_disinfestation.disinfected_product_unit:
                    disinfected_product_unit = str(certificate_of_disinfestation.disinfected_product_unit.name_ru)
                disinfected_product_unit = ''
                if certificate_of_disinfestation.disinfected_product_unit:
                    disinfected_product_unit = str(certificate_of_disinfestation.disinfected_product_unit.name_ru)
                organization_activity_type = certificate_of_disinfestation.organization_activity_type.name if certificate_of_disinfestation.organization_activity_type else '-'
                row_num = row_num + 1
                ws.write(row_num, 0, certificate_of_disinfestation.region.name_ru, font_style)
                ws.write(row_num, 1, certificate_of_disinfestation.number, font_style)
                ws.write(row_num, 2, certificate_of_disinfestation.given_date, font_style)
                ws.write(row_num, 3, certificate_of_disinfestation.organization_name, font_style)
                ws.write(row_num, 4, certificate_of_disinfestation.organization_tin, font_style)
                ws.write(row_num, 5, certificate_of_disinfestation.disinfected_product, font_style)
                ws.write(row_num, 6, certificate_of_disinfestation.disinfected_product_amount, font_style)
                ws.write(row_num, 7, disinfected_product_unit, font_style)
                ws.write(row_num, 8, certificate_of_disinfestation.disinfected_building_volume, font_style)
                ws.write(row_num, 9, certificate_of_disinfestation.disinfected_building_unit.name_ru, font_style)
                ws.write(row_num, 10, certificate_of_disinfestation.declaration_price, font_style)
                ws.write(row_num, 11, certificate_of_disinfestation.total_price, font_style)
                ws.write(row_num, 12, certificate_of_disinfestation.insecticide.name if certificate_of_disinfestation.insecticide else '', font_style)
                ws.write(row_num, 13, certificate_of_disinfestation.insecticide_dosage, font_style)
                ws.write(row_num, 14, certificate_of_disinfestation.expended_insecticide_amount, font_style)
                ws.write(row_num, 15, certificate_of_disinfestation.disinfected_object.name, font_style)
                ws.write(row_num, 16, certificate_of_disinfestation.district.name_ru, font_style)
                ws.write(row_num, 17, certificate_of_disinfestation.get_type_display(), font_style)
                ws.write(row_num, 18, organization_activity_type, font_style)
                ws.write(row_num, 19, certificate_of_disinfestation.fumigator.name_ru, font_style)
                ws.write(row_num, 20, certificate_of_disinfestation.inspector.name_ru, font_style)
                ws.write(row_num, 21, certificate_of_disinfestation.get_disinfestation_type_display(), font_style)
            wb.save(response)
        return response


class DisinfectedObjectsReport(View):
    template_name = 'fumigation/disinfection_objects.html'

    def get(self, request, *args, **kwargs):

        post = request.GET

        if post.get('region_pk'):
            region_pk = int(post.get('region_pk'))
            beginning_of_interval = post.get('beginning_of_interval')
            end_of_interval = post.get('end_of_interval')
            chosen_region = Region.objects.get(pk=region_pk)
            show_fumigators = 'true'
        else:
            chosen_date = date.today()
            chosen_date_year = chosen_date.year
            chosen_date_month = chosen_date.month
            beginning_of_interval = date(chosen_date_year, chosen_date_month, 1).strftime('%Y-%m-%d')
            end_of_interval = chosen_date.strftime('%Y-%m-%d')
            chosen_region = request.user.point.region
        m3 = Unit.objects.get(code='113')
        m2 = Unit.objects.get(code='055')
        inspections = Region.objects.filter(pk__lte=14).order_by('pk')
        disinfected_object_data = {'number': 0, 'inspection': '', 'disinfected_object': '', 'm3': 0, 'm2': 0}
        disinfected_objects_data = []

        if beginning_of_interval and end_of_interval and chosen_region:
            certificates_of_disinfestation_in_m3 = CertificateOfDisinfestation.objects.filter(
                disinfected_building_unit=m3, given_date__gte=beginning_of_interval, given_date__lte=end_of_interval)
            certificates_of_disinfestation_in_m2 = CertificateOfDisinfestation.objects.filter(
                disinfected_building_unit=m2, given_date__gte=beginning_of_interval, given_date__lte=end_of_interval)
            disinfected_objects = DisinfectedObject.objects.all()
            if chosen_region.pk == 15:
                for disinfected_object in disinfected_objects:
                    certificates_of_disinfestation_in_disinfected_object_and_m3 = certificates_of_disinfestation_in_m3.filter(
                        disinfected_object=disinfected_object)
                    certificates_of_disinfestation_in_disinfected_object_and_m2 = certificates_of_disinfestation_in_m2.filter(
                        disinfected_object=disinfected_object)
                    disinfected_object_volume_in_m3 = \
                        certificates_of_disinfestation_in_disinfected_object_and_m3.aggregate(
                            Sum('disinfected_building_volume'))['disinfected_building_volume__sum']
                    disinfected_object_volume_in_m2 = \
                        certificates_of_disinfestation_in_disinfected_object_and_m2.aggregate(
                            Sum('disinfected_building_volume'))['disinfected_building_volume__sum']
                    print('inspections')
                    print(len(inspections))
                    for inspection in inspections:
                        disinfected_object_data = {'number': 0, 'inspection': '', 'disinfected_object': '', 'm3': 0,
                                                   'm2': 0}
                        disinfected_object_volume_in_region_and_m3 = \
                            certificates_of_disinfestation_in_disinfected_object_and_m3.filter(
                                region=inspection).aggregate(
                                Sum('disinfected_building_volume'))['disinfected_building_volume__sum']
                        disinfected_object_volume_in_region_and_m2 = \
                            certificates_of_disinfestation_in_disinfected_object_and_m2.filter(
                                region=inspection).aggregate(Sum('disinfected_building_volume'))[
                                'disinfected_building_volume__sum']
                        disinfected_object_data['number'] = str(inspection.pk)
                        disinfected_object_data['inspection'] = inspection.name_ru
                        if str(inspection.pk) == '8':
                            disinfected_object_data['disinfected_object'] = disinfected_object.name
                        disinfected_object_data[
                            'm3'] = disinfected_object_volume_in_region_and_m3 if disinfected_object_volume_in_region_and_m3 else 0
                        disinfected_object_data[
                            'm2'] = disinfected_object_volume_in_region_and_m2 if disinfected_object_volume_in_region_and_m2 else 0
                        disinfected_objects_data.append(disinfected_object_data)
                    disinfected_object_data = {'number': 0, 'inspection': '', 'disinfected_object': '', 'm3': 0,
                                               'm2': 0}
                    disinfected_object_data['number'] = '15'
                    disinfected_object_data['inspection'] = 'Итого'
                    disinfected_object_data[
                        'm3'] = disinfected_object_volume_in_m3 if disinfected_object_volume_in_m3 else 0
                    disinfected_object_data[
                        'm2'] = disinfected_object_volume_in_m2 if disinfected_object_volume_in_m2 else 0
                    disinfected_objects_data.append(disinfected_object_data)
            else:
                certificates_of_disinfestation_in_m3 = certificates_of_disinfestation_in_m3.filter(region=chosen_region)
                certificates_of_disinfestation_in_m2 = certificates_of_disinfestation_in_m2.filter(region=chosen_region)
                disinfected_objects_volume_in_m3 = \
                    certificates_of_disinfestation_in_m3.aggregate(Sum('disinfected_building_volume'))[
                        'disinfected_building_volume__sum']
                disinfected_objects_volume_in_m2 = \
                    certificates_of_disinfestation_in_m2.aggregate(Sum('disinfected_building_volume'))[
                        'disinfected_building_volume__sum']
                for disinfected_object in disinfected_objects:
                    certificates_of_disinfestation_in_disinfected_object_and_m3 = certificates_of_disinfestation_in_m3.filter(
                        disinfected_object=disinfected_object)
                    certificates_of_disinfestation_in_disinfected_object_and_m2 = certificates_of_disinfestation_in_m2.filter(
                        disinfected_object=disinfected_object)
                    disinfected_object_data = {'number': 0, 'inspection': '', 'disinfected_object': '', 'm3': 0,
                                               'm2': 0}
                    disinfected_object_volume_in_region_and_m3 = \
                        certificates_of_disinfestation_in_disinfected_object_and_m3.aggregate(
                            Sum('disinfected_building_volume'))['disinfected_building_volume__sum']
                    disinfected_object_volume_in_region_and_m2 = \
                        certificates_of_disinfestation_in_disinfected_object_and_m2.aggregate(
                            Sum('disinfected_building_volume'))['disinfected_building_volume__sum']
                    disinfected_object_data['disinfected_object'] = disinfected_object.name
                    disinfected_object_data[
                        'm3'] = disinfected_object_volume_in_region_and_m3 if disinfected_object_volume_in_region_and_m3 else 0
                    disinfected_object_data[
                        'm2'] = disinfected_object_volume_in_region_and_m2 if disinfected_object_volume_in_region_and_m2 else 0
                    disinfected_objects_data.append(disinfected_object_data)
                disinfected_object_data = {'number': 0, 'inspection': '', 'disinfected_object': '', 'm3': 0, 'm2': 0}
                disinfected_object_data['disinfected_object'] = 'Итого'
                disinfected_object_data[
                    'm3'] = disinfected_objects_volume_in_m3 if disinfected_objects_volume_in_m3 else 0
                disinfected_object_data[
                    'm2'] = disinfected_objects_volume_in_m2 if disinfected_objects_volume_in_m2 else 0
                disinfected_objects_data.append(disinfected_object_data)
        return render(request, self.template_name, {
            'beginning_of_interval': beginning_of_interval,
            'end_of_interval': end_of_interval,
            'chosen_region': chosen_region,
            'regions': inspections,
            'disinfected_objects_data': disinfected_objects_data,
        })


class DownloadDisinfectedObjectsReport(View):

    def get(self, request, *args, **kwargs):
        post = request.GET
        region_pk = int(post.get('region_pk'))
        beginning_of_interval = post.get('beginning_of_interval')
        end_of_interval = post.get('end_of_interval')
        chosen_region = Region.objects.get(pk=region_pk)
        file_name = 'obezzarajennie_obekti' + '_for_' + chosen_region.name_en + '(' + beginning_of_interval + '___' + end_of_interval + ')'

        m3 = Unit.objects.get(code='113')
        m2 = Unit.objects.get(code='055')

        response = HttpResponse(content_type='application/ms-excel')

        # decide file name
        response['Content-Disposition'] = f'attachment; filename="{file_name}.xls"'

        # creating workbook
        wb = xlwt.Workbook(encoding='utf-8')

        # adding sheet
        ws = wb.add_sheet("sheet1")

        # Sheet header, first row
        row_num = 0

        font_style = xlwt.XFStyle()
        # headers are bold
        font_style.font.bold = True

        # column header names, you can use your own headers here
        if region_pk == 15:
            columns = ['№', 'Территориальные инспекции', 'Обеззараженные объекты', 'м3', 'м2']
        else:
            columns = ['№', 'Обеззараженные объекты', 'м3', 'м2']

        # write column headers in sheet
        for col_num in range(len(columns)):
            ws.write(row_num, col_num, columns[col_num], font_style)

        # Sheet body, remaining rows
        font_style = xlwt.XFStyle()

        if beginning_of_interval and end_of_interval and chosen_region:
            certificates_of_disinfestation_in_m3 = CertificateOfDisinfestation.objects.filter(
                disinfected_building_unit=m3, given_date__gte=beginning_of_interval, given_date__lte=end_of_interval)
            certificates_of_disinfestation_in_m2 = CertificateOfDisinfestation.objects.filter(
                disinfected_building_unit=m2, given_date__gte=beginning_of_interval, given_date__lte=end_of_interval)
            if region_pk == 15:
                disinfected_objects = DisinfectedObject.objects.all()
                inspections = Region.objects.filter(pk__lte=14).order_by('pk')
                for disinfected_object in disinfected_objects:
                    certificates_of_disinfestation_in_disinfected_object_and_m3 = certificates_of_disinfestation_in_m3.filter(
                        disinfected_object=disinfected_object)
                    certificates_of_disinfestation_in_disinfected_object_and_m2 = certificates_of_disinfestation_in_m2.filter(
                        disinfected_object=disinfected_object)
                    disinfected_object_volume_in_m3 = \
                        certificates_of_disinfestation_in_disinfected_object_and_m3.aggregate(
                            Sum('disinfected_building_volume'))['disinfected_building_volume__sum']
                    disinfected_object_volume_in_m2 = \
                        certificates_of_disinfestation_in_disinfected_object_and_m2.aggregate(
                            Sum('disinfected_building_volume'))['disinfected_building_volume__sum']
                    for inspection in inspections:
                        disinfected_object_volume_in_region_and_m3 = \
                            certificates_of_disinfestation_in_disinfected_object_and_m3.filter(
                                region=inspection).aggregate(
                                Sum('disinfected_building_volume'))['disinfected_building_volume__sum']
                        disinfected_object_volume_in_region_and_m2 = \
                            certificates_of_disinfestation_in_disinfected_object_and_m2.filter(
                                region=inspection).aggregate(
                                Sum('disinfected_building_volume'))['disinfected_building_volume__sum']
                        row_num = row_num + 1
                        ws.write(row_num, 0, str(inspection.pk), font_style)
                        ws.write(row_num, 1, inspection.name_ru, font_style)
                        if str(inspection.pk) == '8':
                            ws.write(row_num, 2, disinfected_object.name, font_style)
                        ws.write(row_num, 3, disinfected_object_volume_in_region_and_m3, font_style)
                        ws.write(row_num, 4, disinfected_object_volume_in_region_and_m2, font_style)
                    row_num = row_num + 1
                    ws.write(row_num, 0, '15', font_style)
                    ws.write(row_num, 1, 'Итого:', font_style)
                    ws.write(row_num, 3, disinfected_object_volume_in_m3, font_style)
                    ws.write(row_num, 4, disinfected_object_volume_in_m2, font_style)
            else:
                disinfected_objects = DisinfectedObject.objects.all()
                certificates_of_disinfestation_in_m3 = certificates_of_disinfestation_in_m3.filter(region=chosen_region)
                certificates_of_disinfestation_in_m2 = certificates_of_disinfestation_in_m2.filter(region=chosen_region)
                disinfected_objects_volume_in_m3 = \
                    certificates_of_disinfestation_in_m3.aggregate(Sum('disinfected_building_volume'))[
                        'disinfected_building_volume__sum']
                disinfected_objects_volume_in_m2 = \
                    certificates_of_disinfestation_in_m2.aggregate(Sum('disinfected_building_volume'))[
                        'disinfected_building_volume__sum']
                for disinfected_object in disinfected_objects:
                    certificates_of_disinfestation_in_disinfected_object_and_m3 = certificates_of_disinfestation_in_m3.filter(
                        disinfected_object=disinfected_object)
                    certificates_of_disinfestation_in_disinfected_object_and_m2 = certificates_of_disinfestation_in_m2.filter(
                        disinfected_object=disinfected_object)
                    disinfected_object_data = {'number': 0, 'inspection': '', 'disinfected_object': '', 'm3': 0,
                                               'm2': 0}
                    disinfected_object_volume_in_region_and_m3 = \
                        certificates_of_disinfestation_in_disinfected_object_and_m3.aggregate(
                            Sum('disinfected_building_volume'))['disinfected_building_volume__sum']
                    disinfected_object_volume_in_region_and_m2 = \
                        certificates_of_disinfestation_in_disinfected_object_and_m2.aggregate(
                            Sum('disinfected_building_volume'))['disinfected_building_volume__sum']
                    disinfected_object_data['disinfected_object'] = disinfected_object.name
                    disinfected_object_data[
                        'm3'] = disinfected_object_volume_in_region_and_m3 if disinfected_object_volume_in_region_and_m3 else 0
                    disinfected_object_data[
                        'm2'] = disinfected_object_volume_in_region_and_m2 if disinfected_object_volume_in_region_and_m2 else 0
                    row_num = row_num + 1
                    ws.write(row_num, 0, row_num, font_style)
                    ws.write(row_num, 1, disinfected_object.name, font_style)
                    ws.write(row_num, 2, disinfected_object_volume_in_region_and_m3, font_style)
                    ws.write(row_num, 3, disinfected_object_volume_in_region_and_m2, font_style)
                disinfected_object_data = {'number': 0, 'inspection': '', 'disinfected_object': '', 'm3': 0, 'm2': 0}
                disinfected_object_data['disinfected_object'] = 'Итого'
                disinfected_object_data[
                    'm3'] = disinfected_objects_volume_in_m3 if disinfected_objects_volume_in_m3 else 0
                disinfected_object_data[
                    'm2'] = disinfected_objects_volume_in_m2 if disinfected_objects_volume_in_m2 else 0
                row_num = row_num + 1
                ws.write(row_num, 0, row_num, font_style)
                ws.write(row_num, 1, 'Итого:', font_style)
                ws.write(row_num, 2, disinfected_objects_volume_in_m3, font_style)
                ws.write(row_num, 3, disinfected_objects_volume_in_m2, font_style)
            wb.save(response)
        return response


class GraphicalMonitoring(TemplateView):
    template_name = 'fumigation/graphical_monitoring.html'

    def get(self, request, *args, **kwargs):

        post = request.GET
        bar_chart_data = {}
        fumigators_table_data = {'inspection': '', 'fumigator': '', 'number_of_certificates_of_disinfestation': 0,
                                 'total_amount': 0, 'volume': 0, 'area': 0, 'volume_and_area': 0}
        fumigators_list = []
        m3 = Unit.objects.get(code='113')
        m2 = Unit.objects.get(code='055')
        inspections = Region.objects.filter(pk__lte=14).order_by('pk')
        show_fumigators = 'false'
        fumigators = {}

        if post.get('region_pk'):
            region_pk = int(post.get('region_pk'))
            beginning_of_interval = post.get('beginning_of_interval')
            end_of_interval = post.get('end_of_interval')
            chosen_region = Region.objects.get(pk=region_pk)
            show_fumigators = 'true'
        else:
            chosen_date = date.today()
            chosen_date_year = chosen_date.year
            chosen_date_month = chosen_date.month
            beginning_of_interval = date(chosen_date_year, chosen_date_month, 1).strftime('%Y-%m-%d')
            end_of_interval = chosen_date.strftime('%Y-%m-%d')
            chosen_region = request.user.point.region

        certificates_of_disinfestation = CertificateOfDisinfestation.objects.filter(
            given_date__gte=beginning_of_interval, given_date__lte=end_of_interval)

        if str(chosen_region.pk) != '15':
            certificates_of_disinfestation = certificates_of_disinfestation.filter(region=chosen_region)
            fumigators = User.objects.filter(username__startswith='f', status=UserStatuses.ACTIVE,
                                             point__region=chosen_region)
            for fumigator in fumigators:
                fumigators_table_data = {'inspection': '', 'fumigator': '',
                                         'number_of_certificates_of_disinfestation': 0,
                                         'total_amount': 0, 'volume': 0, 'area': 0, 'volume_and_area': 0}
                certificates_of_disinfestation_for_fumigator = certificates_of_disinfestation.filter(
                    fumigator=fumigator)
                if certificates_of_disinfestation_for_fumigator:
                    disinfected_building_volume_for_fumigator = \
                        certificates_of_disinfestation_for_fumigator.filter(disinfected_building_unit=m3).aggregate(
                            Sum('disinfected_building_volume'))['disinfected_building_volume__sum']
                    disinfected_building_volume_for_fumigator = disinfected_building_volume_for_fumigator if disinfected_building_volume_for_fumigator else 0

                    disinfected_building_area_for_fumigator = \
                        certificates_of_disinfestation_for_fumigator.filter(disinfected_building_unit=m2).aggregate(
                            Sum('disinfected_building_volume'))['disinfected_building_volume__sum']
                    disinfected_building_area_for_fumigator = disinfected_building_area_for_fumigator if disinfected_building_area_for_fumigator else 0

                    total_amount_in_inspector = \
                        certificates_of_disinfestation_for_fumigator.aggregate(Sum('total_price'))['total_price__sum']
                    bar_chart_data[fumigator.name_ru.split()[0]] = total_amount_in_inspector
                    total_amount_in_inspector = format(int(total_amount_in_inspector),
                                                       ",") if total_amount_in_inspector else 0

                    fumigators_table_data['inspection'] = chosen_region.name_ru
                    fumigators_table_data['fumigator'] = fumigator.name_ru
                    fumigators_table_data[
                        'number_of_certificates_of_disinfestation'] = certificates_of_disinfestation_for_fumigator.count()
                    fumigators_table_data['total_amount'] = total_amount_in_inspector
                    fumigators_table_data['volume'] = disinfected_building_volume_for_fumigator
                    fumigators_table_data['area'] = disinfected_building_area_for_fumigator
                    fumigators_table_data[
                        'volume_and_area'] = disinfected_building_volume_for_fumigator + disinfected_building_area_for_fumigator
                    print('fumigators_table_data')
                    print(fumigators_table_data)
                    fumigators_list.append(fumigators_table_data)
        else:
            for inspection in inspections:
                total_amount_in_inspection = \
                    certificates_of_disinfestation.filter(region=inspection).aggregate(Sum('total_price'))[
                        'total_price__sum']
                if total_amount_in_inspection:
                    if inspection.pk == 1:
                        bar_chart_data[inspection.name_ru.split()[1]] = total_amount_in_inspection
                    else:
                        bar_chart_data[inspection.name_ru.split()[0]] = total_amount_in_inspection
                else:
                    if inspection.pk == 1:
                        bar_chart_data[inspection.name_ru.split()[1]] = 0
                    else:
                        bar_chart_data[inspection.name_ru.split()[0]] = 0

            if show_fumigators == 'true':
                fumigators = User.objects.filter(username__startswith='f', status=UserStatuses.ACTIVE)
                for fumigator in fumigators:
                    fumigators_table_data = {'inspection': '', 'fumigator': '',
                                             'number_of_certificates_of_disinfestation': 0,
                                             'total_amount': 0, 'volume': 0, 'area': 0, 'volume_and_area': 0}
                    certificates_of_disinfestation_for_fumigator = certificates_of_disinfestation.filter(
                        fumigator=fumigator)

                    if certificates_of_disinfestation_for_fumigator:
                        disinfected_building_volume_for_fumigator = \
                            certificates_of_disinfestation_for_fumigator.filter(disinfected_building_unit=m3).aggregate(
                                Sum('disinfected_building_volume'))['disinfected_building_volume__sum']
                        disinfected_building_volume_for_fumigator = disinfected_building_volume_for_fumigator if disinfected_building_volume_for_fumigator else 0

                        disinfected_building_area_for_fumigator = \
                            certificates_of_disinfestation_for_fumigator.filter(disinfected_building_unit=m2).aggregate(
                                Sum('disinfected_building_volume'))['disinfected_building_volume__sum']
                        disinfected_building_area_for_fumigator = disinfected_building_area_for_fumigator if disinfected_building_area_for_fumigator else 0

                        total_amount_in_inspector = \
                            certificates_of_disinfestation_for_fumigator.aggregate(Sum('total_price'))[
                                'total_price__sum']
                        total_amount_in_inspector = format(int(total_amount_in_inspector),
                                                           ",") if total_amount_in_inspector else 0

                        fumigators_table_data['inspection'] = fumigator.point.region.name_ru
                        fumigators_table_data['fumigator'] = fumigator.name_ru
                        fumigators_table_data[
                            'number_of_certificates_of_disinfestation'] = certificates_of_disinfestation_for_fumigator.count()
                        fumigators_table_data['total_amount'] = total_amount_in_inspector
                        fumigators_table_data['volume'] = disinfected_building_volume_for_fumigator
                        fumigators_table_data['area'] = disinfected_building_area_for_fumigator
                        fumigators_table_data[
                            'volume_and_area'] = disinfected_building_volume_for_fumigator + disinfected_building_area_for_fumigator
                        print('fumigators_table_data')
                        print(fumigators_table_data)
                        fumigators_list.append(fumigators_table_data)
        print('fumigators_list')
        print(fumigators_list)
        number_of_certificates_of_disinfestation = certificates_of_disinfestation.count()
        certificates_of_disinfestation_in_m3 = \
            certificates_of_disinfestation.filter(disinfected_building_unit=m3).aggregate(
                Sum('disinfected_building_volume'))['disinfected_building_volume__sum']
        certificates_of_disinfestation_in_m2 = \
            certificates_of_disinfestation.filter(disinfected_building_unit=m2).aggregate(
                Sum('disinfected_building_volume'))['disinfected_building_volume__sum']

        total_amount_of_certificates_of_disinfestation = certificates_of_disinfestation.aggregate(Sum('total_price'))[
            'total_price__sum']
        total_amount_of_certificates_of_disinfestation = format(int(total_amount_of_certificates_of_disinfestation),
                                                                ",") if total_amount_of_certificates_of_disinfestation else 0
        return render(request, self.template_name, {
            'beginning_of_interval': beginning_of_interval,
            'end_of_interval': end_of_interval,
            'chosen_region': chosen_region,
            'regions': inspections,
            'number_of_certificates_of_disinfestation': number_of_certificates_of_disinfestation,
            'certificates_of_disinfestation_in_m3': certificates_of_disinfestation_in_m3,
            'certificates_of_disinfestation_in_m2': certificates_of_disinfestation_in_m2,
            'total_amount_of_certificates_of_disinfestation': total_amount_of_certificates_of_disinfestation,
            'bar_chart_data': bar_chart_data,
            'show_fumigators': show_fumigators,
            'fumigators_list': fumigators_list,
        })


class ViewReportOfChambers(TemplateView):
    template_name = 'fumigation/report_of_chambers.html'

    def get(self, request, *args, **kwargs):
        is_republic_manager = request.user.groups.filter(name='Republic Manager Fumigator').exists()
        region = request.user.point.region
        fumigation_chambers = FumigationChamber.objects
        if region.pk == 15:
            fumigation_chambers = fumigation_chambers.all()
        else:
            fumigation_chambers = fumigation_chambers.filter(region=region)

        if request.GET.get('number'):
            fumigation_chambers = fumigation_chambers.filter(number=request.GET.get('number'))

        if not fumigation_chambers:
            messages.warning(request, '<i class="fas fa-ban"> Не найден</i>')
        else:
            fumigation_chambers = fumigation_chambers.order_by('region__name_ru')
        paginator = Paginator(fumigation_chambers, 20)
        page = request.GET.get('page') if request.GET.get('page') else 1
        try:
            fumigation_chambers = paginator.page(page)
        except PageNotAnInteger:
            fumigation_chambers = paginator.page(1)
        except EmptyPage:
            fumigation_chambers = paginator.page(paginator.num_pages)
        return render(request, self.template_name, {
            'page': int(page),
            'fumigation_chambers': fumigation_chambers,
            'is_republic_manager': is_republic_manager,
            'total_num_of_apps': paginator.count,
            'num_pages': range(1, paginator.num_pages + 1),
            'regions': Region.objects.filter(pk__lt=15)
        })


class ChangeChamberRegion(View):
    def post(self, request, *args, **kwargs):
        print('Bismillahir rohmanir rohiym.')
        if not request.user.groups.filter(name='Republic Manager Fumigator').exists():
            messages.error(request, "У вас нет доступа.")
            return HttpResponseRedirect(reverse('fumigation:view_report_of_chambers'))

        try:
            fumigation_chamber = FumigationChamber.objects.get(pk=kwargs.get('pk'))
        except FumigationChamber.DoesNotExist:
            messages.error(request, "Не существует.")
            return HttpResponseRedirect(reverse('fumigation:view_report_of_chambers'))
        fumigation_chamber.region_id = request.POST.get('region_pk')
        fumigation_chamber.save()
        messages.success(request, 'Успешно сделано.')
        return HttpResponseRedirect(reverse('fumigation:view_report_of_chambers') + '?number=' + str(fumigation_chamber.number))


class DeleteChamber(View):
    def get(self, request, *args, **kwargs):
        print('Bismillahir rohmanir rohiym.')
        if not request.user.groups.filter(name='Republic Manager Fumigator').exists():
            messages.error(request, "У вас нет доступа.")
            return HttpResponseRedirect(reverse('fumigation:view_report_of_chambers'))

        try:
            fumigation_chamber = FumigationChamber.objects.get(pk=kwargs.get('pk'))
        except FumigationChamber.DoesNotExist:
            messages.error(request, "Не существует.")
            return HttpResponseRedirect(reverse('fumigation:view_report_of_chambers'))
        fumigation_chamber.is_active = False
        fumigation_chamber.save()
        messages.success(request, 'Успешно сделано.')
        return HttpResponseRedirect(reverse('fumigation:view_report_of_chambers'))


class ReportOfChemicals(TemplateView):
    template_name = 'fumigation/report_of_chemicals.html'

    def get(self, request, *args, **kwargs):

        post = request.GET

        inspections = Region.objects.filter(pk__lte=14)
        choosen_region = request.user.point.region
        unapproved_received_insecticide_exchanges = None
        unapproved_sent_insecticide_exchanges = None
        exchanged_insecticides = None

        chosen_date = date.today()
        chosen_date_year = chosen_date.year
        chosen_date_month = chosen_date.month
        beginning_of_interval = date(chosen_date_year, chosen_date_month, 1).strftime('%Y-%m-%d')
        end_of_interval = chosen_date.strftime('%Y-%m-%d')
        last_month_date_format = (datetime.strptime(beginning_of_interval, '%Y-%m-%d') - timedelta(1))
        last_month = last_month_date_format.strftime('%Y-%m-%d')
        last_month_insecticides_remainders = InsecticidesMonthlyRemainder.objects.filter(region=choosen_region,
                                                                                         end_of_month=last_month)
        if last_month_insecticides_remainders:
            if post.get('beginning_of_interval'):
                beginning_of_interval = post.get('beginning_of_interval')
                end_of_interval = post.get('end_of_interval')
        else:
            beginning_of_interval = date(last_month_date_format.year, last_month_date_format.month, 1).strftime(
                '%Y-%m-%d')
            end_of_interval = last_month

        if last_month_insecticides_remainders and choosen_region.pk == 15:
            regions = Region.objects.all().order_by('pk')
        else:
            regions = Region.objects.filter(pk=choosen_region.pk)

        unapproved_sent_insecticide_exchanges = InsecticideExchange.all_objects.filter(sender_region=choosen_region,
                                                                                       is_active=False)
        unapproved_received_insecticide_exchanges = InsecticideExchange.all_objects.filter(
            receiver_region=choosen_region, is_active=False)
        fumigation_formulae = FumigationFormula.objects.all()
        remainder_month = (datetime.strptime(beginning_of_interval, '%Y-%m-%d') - timedelta(1)).strftime('%Y-%m-%d')
        report_table_data_list = []
        report_table_data_dictionary = {'inspection_name': '', 'remainder_at_beginning_of_month_dictionary': {},
                                        'received_insecticides_dictionary': {}, 'spent_insecticides_dictionary': {},
                                        'remainder_at_end_of_month_dictionary': {},
                                        'number_of_certificates_of_disinfestation': 0}
        remainder_at_beginning_of_month_list = []
        remainder_at_beginning_of_month_dictionary = {}
        exchanged_insecticides_dictionary = {}
        spent_insecticides_dictionary = {}
        received_insecticides_dictionary = {}
        remainder_at_end_of_month_dictionary = {}

        if beginning_of_interval and end_of_interval:
            certificates_of_disinfestation = CertificateOfDisinfestation.objects.filter(
                given_date__gte=beginning_of_interval, given_date__lte=end_of_interval)
            exchanged_insecticides = InsecticideExchange.objects.filter(exchanged_date__gte=beginning_of_interval,
                                                                        exchanged_date__lte=end_of_interval)
            insecticides_monthly_remainders = InsecticidesMonthlyRemainder.objects.filter(end_of_month=remainder_month)
            for region in regions:
                report_table_data_dictionary = {'inspection_name': region.name_ru,
                                                'remainder_at_beginning_of_month_dictionary': {},
                                                'received_insecticides_dictionary': {},
                                                'spent_insecticides_dictionary': {},
                                                'remainder_at_end_of_month_dictionary': {},
                                                'number_of_certificates_of_disinfestation': 0}
                insecticides_monthly_remainders_in_region = insecticides_monthly_remainders.filter(region=region)
                sent_exchanged_insecticides = exchanged_insecticides.filter(sender_region=region)
                received_exchanged_insecticides = exchanged_insecticides.filter(receiver_region=region)
                certificates_of_disinfestation_in_region = certificates_of_disinfestation.filter(region=region)
                counter = 0
                for fumigation_formula in fumigation_formulae:
                    counter = counter + 1
                    if counter == 1:
                        remainder_at_beginning_of_month_dictionary = {}
                        received_insecticides_dictionary = {}
                        spent_insecticides_dictionary = {}
                        remainder_at_end_of_month_dictionary = {}
                    insecticides_monthly_remainder_in_region = insecticides_monthly_remainders_in_region.filter(
                        fumigation_formula=fumigation_formula).first()
                    insecticides_monthly_remainder_in_region_amount = insecticides_monthly_remainder_in_region.amount if insecticides_monthly_remainder_in_region else 0

                    received_insecticides_amount = \
                        received_exchanged_insecticides.filter(insecticide__formula=fumigation_formula).aggregate(
                            Sum('amount'))['amount__sum']
                    received_insecticides_amount = received_insecticides_amount if received_insecticides_amount else 0

                    sent_insecticides_amount = \
                        sent_exchanged_insecticides.filter(insecticide__formula=fumigation_formula).aggregate(
                            Sum('amount'))['amount__sum']
                    sent_insecticides_amount = sent_insecticides_amount if sent_insecticides_amount else 0

                    spent_insecticides_amount = \
                        certificates_of_disinfestation_in_region.filter(
                            insecticide__formula=fumigation_formula).aggregate(
                            Sum('expended_insecticide_amount'))['expended_insecticide_amount__sum']
                    spent_insecticides_amount = spent_insecticides_amount if spent_insecticides_amount else 0
                    spent_insecticides_amount = spent_insecticides_amount + sent_insecticides_amount

                    remainder_at_beginning_of_month_dictionary[fumigation_formula.formula] = round(
                        int(insecticides_monthly_remainder_in_region_amount) / 1000, 1)
                    received_insecticides_dictionary[fumigation_formula.formula] = round(
                        int(received_insecticides_amount) / 1000, 1)
                    spent_insecticides_dictionary[fumigation_formula.formula] = round(
                        int(spent_insecticides_amount) / 1000, 1)
                    remainder_at_end_of_month_dictionary[fumigation_formula.formula] = round(int(
                        insecticides_monthly_remainder_in_region_amount + received_insecticides_amount - spent_insecticides_amount) / 1000,
                                                                                             1)
                report_table_data_dictionary[
                    'remainder_at_beginning_of_month_dictionary'] = remainder_at_beginning_of_month_dictionary
                report_table_data_dictionary['received_insecticides_dictionary'] = received_insecticides_dictionary
                report_table_data_dictionary['spent_insecticides_dictionary'] = spent_insecticides_dictionary
                report_table_data_dictionary[
                    'remainder_at_end_of_month_dictionary'] = remainder_at_end_of_month_dictionary
                report_table_data_dictionary[
                    'number_of_certificates_of_disinfestation'] = certificates_of_disinfestation_in_region.count()
                report_table_data_list.append(report_table_data_dictionary)
        fumigation_insecticides = FumigationInsecticide.objects.all()
        if choosen_region.pk != 15:
            exchanged_insecticides = exchanged_insecticides.filter(
                Q(receiver_region=choosen_region) | Q(sender_region=choosen_region))
        return render(request, self.template_name, {
            'beginning_of_interval': beginning_of_interval,
            'end_of_interval': end_of_interval,
            'report_table_data_list': report_table_data_list,
            'fumigation_formulae': fumigation_formulae,
            'remainder_month': remainder_month,
            'inspections': inspections,
            'fumigation_insecticides': fumigation_insecticides,
            'unapproved_received_insecticide_exchanges': unapproved_received_insecticide_exchanges,
            'unapproved_sent_insecticide_exchanges': unapproved_sent_insecticide_exchanges,
            'exchanged_insecticides': exchanged_insecticides,
            'last_month_insecticides_remainders': last_month_insecticides_remainders,
            'last_month': last_month_date_format.strftime('%B-%Y'),
        })


class ApproveLastMonthInsecticidesRemainder(View):

    def post(self, request, *args, **kwargs):
        choosen_region = request.user.point.region

        chosen_date = date.today()
        chosen_date_year = chosen_date.year
        chosen_date_month = chosen_date.month
        last_month_date_format = (datetime.strptime(date(chosen_date_year, chosen_date_month, 1).strftime('%Y-%m-%d'),
                                                    '%Y-%m-%d') - timedelta(1))
        last_month = last_month_date_format.strftime('%Y-%m-%d')
        beginning_of_interval = date(last_month_date_format.year, last_month_date_format.month, 1).strftime('%Y-%m-%d')
        end_of_interval = last_month
        last_month_insecticides_remainders = InsecticidesMonthlyRemainder.objects.filter(region=choosen_region,
                                                                                         end_of_month=last_month)
        if not last_month_insecticides_remainders:
            fumigation_formulae = FumigationFormula.objects.all()
            remainder_month = (datetime.strptime(beginning_of_interval, '%Y-%m-%d') - timedelta(1)).strftime('%Y-%m-%d')
            remainder_at_end_of_month = 0

            if beginning_of_interval and end_of_interval:
                certificates_of_disinfestation = CertificateOfDisinfestation.objects.filter(
                    given_date__gte=beginning_of_interval, given_date__lte=end_of_interval)
                exchanged_insecticides = InsecticideExchange.objects.filter(exchanged_date__gte=beginning_of_interval,
                                                                            exchanged_date__lte=end_of_interval)
                insecticides_monthly_remainders = InsecticidesMonthlyRemainder.objects.filter(
                    end_of_month=remainder_month)
                region = choosen_region
                insecticides_monthly_remainders_in_region = insecticides_monthly_remainders.filter(region=region)
                sent_exchanged_insecticides = exchanged_insecticides.filter(sender_region=region)
                received_exchanged_insecticides = exchanged_insecticides.filter(receiver_region=region)
                certificates_of_disinfestation_in_region = certificates_of_disinfestation.filter(region=region)
                counter = 0
                for fumigation_formula in fumigation_formulae:
                    counter = counter + 1
                    if counter == 1:
                        remainder_at_beginning_of_month_dictionary = {}
                        received_insecticides_dictionary = {}
                        spent_insecticides_dictionary = {}
                        remainder_at_end_of_month_dictionary = {}
                    insecticides_monthly_remainder_in_region = insecticides_monthly_remainders_in_region.filter(
                        fumigation_formula=fumigation_formula).first()
                    insecticides_monthly_remainder_in_region_amount = insecticides_monthly_remainder_in_region.amount if insecticides_monthly_remainder_in_region else 0

                    received_insecticides_amount = \
                        received_exchanged_insecticides.filter(insecticide__formula=fumigation_formula).aggregate(
                            Sum('amount'))['amount__sum']
                    received_insecticides_amount = received_insecticides_amount if received_insecticides_amount else 0

                    sent_insecticides_amount = \
                        sent_exchanged_insecticides.filter(insecticide__formula=fumigation_formula).aggregate(
                            Sum('amount'))['amount__sum']
                    sent_insecticides_amount = sent_insecticides_amount if sent_insecticides_amount else 0

                    spent_insecticides_amount = \
                        certificates_of_disinfestation_in_region.filter(
                            insecticide__formula=fumigation_formula).aggregate(
                            Sum('expended_insecticide_amount'))['expended_insecticide_amount__sum']
                    spent_insecticides_amount = spent_insecticides_amount if spent_insecticides_amount else 0
                    spent_insecticides_amount = spent_insecticides_amount + sent_insecticides_amount
                    remainder_at_end_of_month = insecticides_monthly_remainder_in_region_amount + received_insecticides_amount - spent_insecticides_amount
                    try:
                        insecticides_monthly_remainder = InsecticidesMonthlyRemainder.objects.create(
                            region=region,
                            fumigation_formula=fumigation_formula,
                            amount=remainder_at_end_of_month,
                            end_of_month=last_month,
                        )
                    except Exception as e:
                        messages.error(request, str(e))
            messages.success(request, 'Муваффақиятли тасдиқланди. Текшириб кўришизни сўраймиз.')
        else:
            messages.error(request,
                           f'{choosen_region.name_local} учун {last_month} сана билан аллақачон тасдиқлаб берилган.')

        return HttpResponseRedirect(reverse('fumigation:view_report_of_chemicals'))


class EditCertificateOfDisinfestationOrganizationTin(View):
    def post(self, request, *args, **kwargs):
        if request.user.groups.filter(name='Republic Manager Fumigator').exists():
            post = request.POST
            organization_tin = post.get('organization_tin', '')
            user = request.user

            try:
                certificate_of_disinfestation = CertificateOfDisinfestation.objects.get(pk=kwargs.get('pk'))
            except CertificateOfDisinfestation.DoesNotExist:
                messages.error(request, "Ushbu AKT sizga tegishli emas.")
                return HttpResponseRedirect(reverse('fumigation:list_certificate_of_disinfestation'))
            certificate_of_disinfestation.organization_tin = organization_tin
            certificate_of_disinfestation.save()
            messages.success(request, f'Ushbu AKT STIR i {organization_tin} ga ozgartirildi.')
        else:
            messages.error(request, 'У вас нет разрешения.')

        return HttpResponseRedirect(reverse('fumigation:list_certificate_of_disinfestation') + '?number=' + str(
            certificate_of_disinfestation.number))


class DownloadReportOfChambers(View):

    def get(self, request, *args, **kwargs):
        post = request.GET
        region_pk = int(post.get('region_pk'))
        beginning_of_interval = post.get('beginning_of_interval')
        end_of_interval = post.get('end_of_interval')
        chosen_region = Region.objects.get(pk=region_pk)
        file_name = 'report_of_chambers' + '_for_' + chosen_region.name_en + '(' + beginning_of_interval + '___' + end_of_interval + ')'

        response = HttpResponse(content_type='application/ms-excel')

        # decide file name
        response['Content-Disposition'] = f'attachment; filename="{file_name}.xls"'

        # creating workbook
        wb = xlwt.Workbook(encoding='utf-8')

        # adding sheet
        ws = wb.add_sheet("sheet1")

        # Sheet header, first row
        row_num = 0

        font_style = xlwt.XFStyle()
        # headers are bold
        font_style.font.bold = True

        # column header names, you can use your own headers here
        columns = ['Область', 'Hомер', 'Общая сумма', 'Объем в м3']

        # write column headers in sheet
        for col_num in range(len(columns)):
            ws.write(row_num, col_num, columns[col_num], font_style)

        # Sheet body, remaining rows
        font_style = xlwt.XFStyle()

        if beginning_of_interval and end_of_interval and chosen_region:
            fumigation_chambers = FumigationChamber.objects.all()
            for fumigation_chamber in fumigation_chambers:
                certificates_of_disinfestation = fumigation_chamber.certificates_of_disinfestation.filter(
                    given_date__gte=beginning_of_interval, given_date__lte=end_of_interval)
                volume = certificates_of_disinfestation.aggregate(Sum('disinfected_building_volume'))[
                    'disinfected_building_volume__sum']
                income = certificates_of_disinfestation.aggregate(Sum('total_price'))['total_price__sum']
                row_num = row_num + 1
                ws.write(row_num, 0, fumigation_chamber.region.name_ru, font_style)
                ws.write(row_num, 1, fumigation_chamber.number, font_style)
                ws.write(row_num, 2, income, font_style)
                ws.write(row_num, 3, volume, font_style)
            wb.save(response)
        return response
