import datetime
import io
import locale
import os

import qrcode
import xlwt
from PyPDF2 import PdfFileReader, PdfFileWriter
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseNotFound
from django.shortcuts import render
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from administration.models import Country, SMSNotification
from administration.statuses import SMSNotificationStatuses, SMSNotificationPurposes
from ppp.models import Biocide, UNIT_CHOICES, PPPRegistrationProtocol, PPPRegistrationProtocolScope
from ppp.statuses import PPPProtocolStatuses


class AddPPPRegistrationProtocolView(TemplateView):
    template_name = 'ppp/protocol/add.html'

    def get(self, request):
        form = None
        return render(request, self.template_name, {
            'form': form,
            'countries': Country.objects.all().order_by('name_ru'),
            'biocides': Biocide.objects.all(),
            'units': UNIT_CHOICES
        })

    def post(self, request, *args, **kwargs):
        post = request.POST
        user = request.user
        if user.has_perm('ppp.add_ppp_registration_protocols'):
            with transaction.atomic():
                plant_type_uz = post.getlist('plant_type_uz[]')
                plant_type_ru = post.getlist('plant_type_ru[]')
                harmful_organisms_uz = post.getlist('harmful_organisms_uz[]')
                harmful_organisms_ru = post.getlist('harmful_organisms_ru[]')
                amount = post.getlist('amount[]')
                unit = post.getlist('unit[]')
                scope_uz = post.getlist('scope_uz[]')
                scope_ru = post.getlist('scope_ru[]')
                day = post.getlist('day[]')
                time = post.getlist('time[]')
                if len(plant_type_uz) > 0 and len(plant_type_uz) == len(plant_type_ru) == len(harmful_organisms_uz) == \
                        len(harmful_organisms_ru) == len(amount) == len(unit) == len(scope_uz) == len(scope_ru):
                    try:
                        ppp_registration_protocol = PPPRegistrationProtocol.objects.create(
                            serial_number=post.get('serial_number'),
                            expire_date=post.get('expire_date'),
                            protocol_number=post.get('protocol_number'),
                            protocol_given_date=post.get('protocol_given_date'),
                            country_id=post.get('country_id'),
                            applicant_tin=post.get('applicant_tin'),
                            applicant_name=post.get('applicant_name'),
                            applicant_phone=post.get('applicant_phone'),
                            biocide_id=post.get('biocide_id'),
                            biocide_trade_name=post.get('biocide_trade_name'),
                            concentration=post.get('concentration'),
                            irritant_substance=post.get('irritant_substance'),
                            registerer=user
                        )

                        if ppp_registration_protocol:
                            for index in range(0, len(plant_type_uz)):
                                PPPRegistrationProtocolScope.objects.create(
                                    ppp_registration_protocol=ppp_registration_protocol,
                                    plant_type_uz=plant_type_uz[index],
                                    plant_type_ru=plant_type_ru[index],
                                    harmful_organisms_uz=harmful_organisms_uz[index],
                                    harmful_organisms_ru=harmful_organisms_ru[index],
                                    amount=amount[index],
                                    unit=unit[index],
                                    scope_uz=scope_uz[index],
                                    scope_ru=scope_ru[index],
                                    day=day[index] if day[index] else None,
                                    time=time[index] if time[index] else None,
                                )
                        messages.success(request, 'Муваффақиятли сақланди.')
                        return HttpResponseRedirect(reverse('ppp:saved_ppp_registration_protocols_list'))
                    except Exception as e:
                        messages.error(request, e)
                        return HttpResponseRedirect(reverse('ppp:saved_ppp_registration_protocols_list'))
                else:
                    messages.error(request, 'Қўллаш доираси формасини тўлдиришда хатолик бор.')
                    return HttpResponseRedirect(reverse('ppp:saved_ppp_registration_protocols_list'))
        else:
            messages.error(request, 'Доступ закрыт!')
            return HttpResponseRedirect(reverse('administration:logout'))


class SavedPPPRegistrationProtocolListView(TemplateView):
    template_name = 'ppp/protocol/saved_list.html'

    def get(self, request):
        user = request.user

        if user.has_perm('ppp.send_to_approve_ppp_registration_protocols') or user.has_perm('ppp.approve_ppp_registration_protocols'):
            protocols = PPPRegistrationProtocol.all_objects.filter(status=PPPProtocolStatuses.SAVED)
        elif user.has_perm('ppp.add_ppp_registration_protocols'):
            protocols = PPPRegistrationProtocol.all_objects.filter(status=PPPProtocolStatuses.SAVED, registerer=user)

        if request.GET.get('applicant_name'):
            protocols = protocols.filter(applicant_name__contains=request.GET.get('applicant_name'))

        paginator = Paginator(protocols, 10)
        page = request.GET.get('page') if request.GET.get('page') else 1
        try:
            protocols = paginator.page(page)
        except PageNotAnInteger:
            protocols = paginator.page(1)
        except EmptyPage:
            protocols = paginator.page(paginator.num_pages)
        if not protocols:
            messages.warning(request, '<i class="fas fa-ban"> Сақланган гувоҳномалар топилмади</i>')
        return render(request, self.template_name, {
            'page': int(page),
            'protocols': protocols,
            'total_num_of_protocols': paginator.count,
            'num_pages': range(1, paginator.num_pages + 1)
        })


class EditPPPRegistrationProtocolView(TemplateView):
    template_name = 'ppp/protocol/edit.html'

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        redirect_url = reverse('ppp:edit_ppp_registration_protocol', kwargs={'pk': kwargs.get('pk')})
        try:
            if user.has_perm('ppp.approve_ppp_registration_protocols'):
                protocol = PPPRegistrationProtocol.all_objects.get(status=PPPProtocolStatuses.PENDING, pk=kwargs.get('pk'))
            elif user.has_perm('ppp.send_to_approve_ppp_registration_protocols'):
                protocol = PPPRegistrationProtocol.all_objects.get(status=PPPProtocolStatuses.SAVED,
                                                                   pk=kwargs.get('pk'))
            elif user.has_perm('ppp.add_ppp_registration_protocols'):
                protocol = PPPRegistrationProtocol.all_objects.get(status=PPPProtocolStatuses.SAVED, registerer=request.user, pk=kwargs.get('pk'))
            else:
                messages.error(request, 'Рухсат йўқ.')
                return HttpResponseRedirect(reverse('administration:logout'))

            kwargs.update({'protocol': protocol, 'redirect_url': redirect_url})
            return super(EditPPPRegistrationProtocolView, self).dispatch(request, *args, **kwargs)
        except Exception as e:
            messages.error(request, e)
            return HttpResponseRedirect(reverse('ppp:saved_ppp_registration_protocols_list'))

    def get(self, request, **kwargs):
        return render(request, self.template_name, {
            'protocol': kwargs.get('protocol'),
            'scopes': kwargs.get('protocol').scopes.all(),
            'countries': Country.objects.all().order_by('name_ru'),
            'biocides': Biocide.objects.all(),
            'units': UNIT_CHOICES,
            'protocol_statuses': PPPProtocolStatuses
        })

    def post(self, request, *args, **kwargs):

        protocol = kwargs.get('protocol')
        redirect_url = kwargs.get('redirect_url')
        post = request.POST

        if post.get('submission_purpose') == 'delete' and protocol.status == PPPProtocolStatuses.SAVED:
            protocol.delete()
            messages.success(request, 'Муваффақиятли ўчирилди.')
            return HttpResponseRedirect(redirect_url)

        if post.get('submission_purpose') == 'sent_to_back' and protocol.status == PPPProtocolStatuses.PENDING:
            protocol.status = PPPProtocolStatuses.SAVED
            protocol.save()
            messages.success(request, 'Муваффақиятли ортга қайтарилди.')
            return HttpResponseRedirect(redirect_url)

        with transaction.atomic():
            protocol.scopes.all().delete()
            try:
                protocol.serial_number = post.get('serial_number')
                protocol.expire_date = post.get('expire_date')
                protocol.protocol_number = post.get('protocol_number')
                protocol.protocol_given_date = post.get('protocol_given_date')
                protocol.country_id = post.get('country_id')
                protocol.applicant_tin = post.get('applicant_tin')
                protocol.applicant_name = post.get('applicant_name')
                protocol.applicant_phone = post.get('applicant_phone')
                protocol.biocide_id = post.get('biocide_id')
                protocol.biocide_trade_name = post.get('biocide_trade_name')
                protocol.concentration = post.get('concentration')
                protocol.irritant_substance = post.get('irritant_substance')

                if post.get('submission_purpose') == 'sent_to_next' and protocol.status == PPPProtocolStatuses.SAVED:
                    protocol.status = PPPProtocolStatuses.PENDING
                    redirect_url = reverse('ppp:saved_ppp_registration_protocols_list')
                    messages.success(request, 'Тасдиқлашга юборилди.')

                if post.get('submission_purpose') == 'approve' and protocol.status == PPPProtocolStatuses.PENDING:
                    redirect_url = reverse('ppp:ppp_registration_protocols_list')
                    biocide = Biocide.objects.get(pk=post.get('biocide_id'))
                    if protocol.order_number:
                        order_number = protocol.order_number
                        given_date = protocol.given_date
                    else:
                        this_year = int(datetime.datetime.now().strftime('%y'))
                        first_four_digits = str(this_year)
                        last_protocol = PPPRegistrationProtocol.all_objects.filter(order_number__startswith=str(first_four_digits)).order_by(
                            'order_number').last()
                        if last_protocol:
                            order_number = int(last_protocol.order_number) + 1
                            biocide_registered_order_number = biocide.yearly_counter + 1
                        else:
                            order_number = this_year * 10000 + 1
                            biocide_registered_order_number = 1

                        biocide.yearly_counter = biocide_registered_order_number
                        biocide.counter += 1
                        biocide.save()
                        given_date = datetime.datetime.today().strftime('%Y-%m-%d')

                    protocol.number = protocol.serial_number + str(order_number)
                    protocol.order_number = order_number
                    protocol.given_date = given_date
                    protocol.biocide_registered_number = biocide.code + '.' + str(biocide_registered_order_number)
                    protocol.biocide_registered_date = given_date
                    protocol.approved_by = request.user
                    protocol.status = PPPProtocolStatuses.APPROVED

                    text = f"O‘SIMLIKLARNI HIMOYA QILISHNING KIMYOVIY VA BIOLOGIK VOSITALARI HAMDA MINERAL VA " \
                           f"MIKROBIOLOGIK O‘G‘ITLARNI RO‘YXATGA OLINGANLIK TO‘G‘RISIDA GUVOHNOMA: https://efito.uz/ppp/registration-protocols/{protocol.serial_number + str(order_number)}/pdf/"

                    SMSNotification.objects.create(
                        text=text,
                        receiver_phone='998' + str(post.get('applicant_phone')),
                        status=SMSNotificationStatuses.REQUESTED,
                        purpose=SMSNotificationPurposes.PPP
                    )

                protocol.save()
            except Exception as e:
                messages.error(request, e)
                return HttpResponseRedirect(redirect_url)

            plant_type_uz = post.getlist('plant_type_uz[]')
            plant_type_ru = post.getlist('plant_type_ru[]')
            harmful_organisms_uz = post.getlist('harmful_organisms_uz[]')
            harmful_organisms_ru = post.getlist('harmful_organisms_ru[]')
            amount = post.getlist('amount[]')
            unit = post.getlist('unit[]')
            scope_uz = post.getlist('scope_uz[]')
            scope_ru = post.getlist('scope_ru[]')
            day = post.getlist('day[]')
            time = post.getlist('time[]')
            delete_scope = post.getlist('delete_scope[]')
            if len(plant_type_uz) > 0 and len(plant_type_uz) == len(plant_type_ru) == len(harmful_organisms_uz) == \
                    len(harmful_organisms_ru) == len(amount) == len(unit) == len(scope_uz) == len(scope_ru):
                try:
                    for index in range(0, len(plant_type_uz)):
                        if delete_scope[index] == 'no' and len(plant_type_uz[index]) > 0:
                            PPPRegistrationProtocolScope.objects.create(
                                ppp_registration_protocol=protocol,
                                plant_type_uz=plant_type_uz[index],
                                plant_type_ru=plant_type_ru[index],
                                harmful_organisms_uz=harmful_organisms_uz[index],
                                harmful_organisms_ru=harmful_organisms_ru[index],
                                amount=amount[index],
                                unit=unit[index],
                                scope_uz=scope_uz[index],
                                scope_ru=scope_ru[index],
                                day=day[index] if day[index] else None,
                                time=time[index] if time[index] else None,
                            )
                    messages.success(request, 'Муваффақиятли сақланди.')
                    return HttpResponseRedirect(redirect_url)
                except Exception as e:
                    messages.error(request, e)
                    return HttpResponseRedirect(redirect_url)
        return HttpResponseRedirect(redirect_url)


class PendingPPPRegistrationProtocolListView(TemplateView):
    template_name = 'ppp/protocol/pending_list.html'

    def get(self, request, **kwargs):
        user = request.user
        if user.has_perm('ppp.approve_ppp_registration_protocols') or user.has_perm('ppp.add_ppp_registration_protocols'):
            protocols = PPPRegistrationProtocol.all_objects.filter(status=PPPProtocolStatuses.PENDING)

            if request.GET.get('applicant_name'):
                protocols = protocols.filter(applicant_name__contains=request.GET.get('applicant_name'))

            paginator = Paginator(protocols, 10)
            page = request.GET.get('page') if request.GET.get('page') else 1
            try:
                protocols = paginator.page(page)
            except PageNotAnInteger:
                protocols = paginator.page(1)
            except EmptyPage:
                protocols = paginator.page(paginator.num_pages)
            if not protocols:
                messages.warning(request, '<i class="fas fa-ban"> Сақланган гувоҳномалар топилмади</i>')
            return render(request, self.template_name, {
                'page': int(page),
                'protocols': protocols,
                'total_num_of_protocols': paginator.count,
                'num_pages': range(1, paginator.num_pages + 1)
            })


class PPPRegistrationProtocolListView(TemplateView):
    template_name = 'ppp/protocol/list.html'

    def get(self, request, **kwargs):
        user = request.user
        if user.has_perm('ppp.list_ppp_registration_protocols'):
            protocols = PPPRegistrationProtocol.objects.all()

            if request.GET.get('number'):
                protocols = protocols.filter(number=request.GET.get('number'))

            paginator = Paginator(protocols, 10)
            page = request.GET.get('page') if request.GET.get('page') else 1
            try:
                protocols = paginator.page(page)
            except PageNotAnInteger:
                protocols = paginator.page(1)
            except EmptyPage:
                protocols = paginator.page(paginator.num_pages)
            if not protocols:
                messages.warning(request, '<i class="fas fa-ban"> Гувоҳномалар топилмади</i>')
            return render(request, self.template_name, {
                'page': int(page),
                'protocols': protocols,
                'biocides': Biocide.objects.all(),
                'total_num_of_protocols': paginator.count,
                'num_pages': range(1, paginator.num_pages + 1)
            })


class PdfVersionView(View):
    def get(self, request, *args, **kwargs):
        fs = FileSystemStorage()
        locale.setlocale(locale.LC_ALL, 'ru_RU')  # to show months in russian messages
        pdfmetrics.registerFont(TTFont('Verdana', 'Verdana.ttf'))
        try:
            protocol = PPPRegistrationProtocol.all_objects.get(number=kwargs.get('number'))
            number = protocol.number
        except:
            try:
                protocol = PPPRegistrationProtocol.all_objects.get(pk=kwargs.get('number'))
                number = str(protocol.pk)
            except:
                return HttpResponseNotFound(str(kwargs.get('number')) + " рақамли ЎСИМЛИКЛАРНИ ҲИМОЯ ҚИЛИШНИНГ КИМЁВИЙ "
                                                                        "ВА БИОЛОГИК ВОСИТАЛАРИ ҲАМДА МИНЕРАЛ ВА "
                                                                        "МИКРОБИОЛОГИК ЎҒИТЛАРНИ РЎЙХАТГА ОЛИНГАНЛИК "
                                                                        "ТЎҒРИСИДА ГУВОҲНОМА мавжуд эмас.")
        file_name = 'ppp_registration_protocol_' + str(number)

        qrcode_link = f'blanks/qr_code/{file_name}.png'  # look up file from media automatically
        if fs.exists(qrcode_link):
            qrcode_image = ImageReader(f'media/blanks/qr_code/{file_name}.png')
        else:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=6,
                border=0,
            )
            qr.add_data(f'https://efito.uz/ppp/registration-protocols/{number}/pdf/')
            qr.make(fit=True)
            img = qr.make_image()
            img.save(f'media/blanks/qr_code/{file_name}.png')
            qrcode_image = ImageReader(f'media/blanks/qr_code/{file_name}.png')

        first_packet = io.BytesIO()

        # create a new PDF with Reportlab
        first_page_one_context = canvas.Canvas(first_packet, pagesize=letter)

        first_page_one_context.setFont('Verdana', 8)

        first_page_one_context.drawString(10.4 * cm, 23 * cm, number)

        applicant_name = protocol.applicant_name
        applicant_name_part_one = ''
        applicant_name_part_two = ''
        for applicant_name in applicant_name.split():
            if len(applicant_name_part_one + applicant_name) < 70 and len(applicant_name_part_two) < 1:
                applicant_name_part_one = applicant_name_part_one + ' ' + applicant_name
            elif len(applicant_name_part_two + applicant_name) < 75:
                applicant_name_part_two = applicant_name_part_two + ' ' + applicant_name

        first_page_one_context.drawString(9.2 * cm, 21.7 * cm, applicant_name_part_one)
        if applicant_name_part_two:
            first_page_one_context.drawString(9.2 * cm, 21.3 * cm, applicant_name_part_two)

        biocide_trade_name_and_etc_uz = protocol.biocide_trade_name + '; ' + protocol.concentration + '; ' + \
                                        protocol.biocide.name_uz + '; ' + protocol.irritant_substance
        biocide_trade_name_and_etc_part_one = ''
        biocide_trade_name_and_etc_part_two = ''
        biocide_trade_name_and_etc_part_three = ''
        biocide_trade_name_and_etc_part_four = ''
        for biocide_trade_name_and_etc in biocide_trade_name_and_etc_uz.split():
            if len(biocide_trade_name_and_etc_part_one + biocide_trade_name_and_etc) < 60 and len(biocide_trade_name_and_etc_part_two) < 1:
                biocide_trade_name_and_etc_part_one = biocide_trade_name_and_etc_part_one + ' ' + biocide_trade_name_and_etc
            elif len(biocide_trade_name_and_etc_part_two + biocide_trade_name_and_etc) < 60 and len(biocide_trade_name_and_etc_part_three) < 1:
                biocide_trade_name_and_etc_part_two = biocide_trade_name_and_etc_part_two + ' ' + biocide_trade_name_and_etc
            elif len(biocide_trade_name_and_etc_part_three + biocide_trade_name_and_etc) < 60 and len(biocide_trade_name_and_etc_part_four) < 1:
                biocide_trade_name_and_etc_part_three = biocide_trade_name_and_etc_part_three + ' ' + biocide_trade_name_and_etc
            elif len(biocide_trade_name_and_etc_part_four + biocide_trade_name_and_etc) < 65:
                biocide_trade_name_and_etc_part_four = biocide_trade_name_and_etc_part_four + ' ' + biocide_trade_name_and_etc
        first_page_one_context.drawString(9.2 * cm, 20.5 * cm, biocide_trade_name_and_etc_part_one)
        if biocide_trade_name_and_etc_part_two:
            first_page_one_context.drawString(9.2 * cm, 20.1 * cm, biocide_trade_name_and_etc_part_two)
        if biocide_trade_name_and_etc_part_three:
            first_page_one_context.drawString(9.2 * cm, 19.5 * cm, biocide_trade_name_and_etc_part_three)
        if biocide_trade_name_and_etc_part_four:
            first_page_one_context.drawString(9.2 * cm, 19.1 * cm, biocide_trade_name_and_etc_part_four)

        counter = 0
        y = 16
        z = 16
        w = 16

        for scope in protocol.scopes.all():
            counter += 1
            # first_page_one_context.drawString(1.8 * cm, y * cm, str(tbotd.ikr_shipment.fito_given_date))
            # first_page_one_context.drawString(1.7 * cm, y * cm, str(tbotd.ikr_shipment.info))
            # first_page_one_context.drawString(1.7 * cm, y * cm, str(tbotd.number))

            plant_type_part_parts_list = []
            plant_type_part = ''
            for plant_type in scope.plant_type_uz.split():
                if len(plant_type_part + plant_type) < 20:
                    plant_type_part = plant_type_part + plant_type + ' '
                else:
                    plant_type_part_parts_list.append(plant_type_part)
                    plant_type_part = plant_type + ' '

            if len(plant_type_part) <= 20:
                plant_type_part_parts_list.append(plant_type_part)  # do not remove this line never ever
            second_counter = 0
            for plant_type_part in plant_type_part_parts_list:
                second_counter += 1
                if second_counter == 1:
                    plant_type_part = f'{counter}. ' + plant_type_part
                first_page_one_context.drawString(3.1 * cm, y * cm, plant_type_part)
                y = y - 0.3
            y -= 0.2

            harmful_organisms_part_parts_list = []
            harmful_organisms_part = ''
            for harmful_organisms in scope.harmful_organisms_uz.split():
                if len(harmful_organisms_part + harmful_organisms) < 20:
                    harmful_organisms_part = harmful_organisms_part + harmful_organisms + ' '
                else:
                    harmful_organisms_part_parts_list.append(harmful_organisms_part)
                    harmful_organisms_part = harmful_organisms + ' '

            if len(harmful_organisms_part) <= 20:
                harmful_organisms_part_parts_list.append(harmful_organisms_part)  # do not remove this line never ever
            second_counter = 0
            for harmful_organisms_part in harmful_organisms_part_parts_list:
                second_counter += 1
                if second_counter == 1:
                    harmful_organisms_part = f'{counter}. ' + harmful_organisms_part
                    first_page_one_context.drawString(10.5 * cm, z * cm, f'{counter}. ' + str(scope.amount) + ' ' + str(UNIT_CHOICES[scope.unit-1][1]))
                first_page_one_context.drawString(6.9 * cm, z * cm, harmful_organisms_part)
                z = z - 0.3
            z -= 0.2

            scope_part_parts_list = []
            scope_part = ''
            for scope in scope.scope_uz.split():
                if len(scope_part + scope) < 35:
                    scope_part = scope_part + scope + ' '
                else:
                    scope_part_parts_list.append(scope_part)
                    scope_part = scope + ' '

            if len(scope_part) <= 35:
                scope_part_parts_list.append(scope_part)  # do not remove this line never ever
            second_counter = 0
            for scope_part in scope_part_parts_list:
                second_counter += 1
                if second_counter == 1:
                    scope_part = f'{counter}. ' + scope_part
                first_page_one_context.drawString(13.1 * cm, w * cm, scope_part)
                w = w - 0.3
            w -= 0.2

        first_page_one_context.drawString(10 * cm, 5.5 * cm, f'№ {protocol.biocide_registered_number}, ' + str(protocol.biocide_registered_date.strftime('%d-%m-%Y') if protocol.biocide_registered_date else ''))
        first_page_one_context.drawString(7.5 * cm, 4 * cm, str(protocol.expire_date.strftime('%d-%m-%Y')))
        first_page_one_context.drawString(12 * cm, 2.2 * cm, protocol.approved_by.name_ru if protocol.approved_by else '')
        first_page_one_context.drawImage(qrcode_image, 17.5 * cm, 1.7 * cm, width=55, height=55, mask='auto')
        first_page_one_context.save()
        first_packet.seek(0)

        for_first_page = PdfFileReader(first_packet)

        second_packet = io.BytesIO()

        # create a new PDF with Reportlab
        second_page_one_context = canvas.Canvas(second_packet, pagesize=letter)
        second_page_one_context.setFont('Verdana', 8)
        second_page_one_context.drawString(10.4 * cm, 23 * cm, number)

        applicant_name = protocol.applicant_name
        applicant_name_part_one = ''
        applicant_name_part_two = ''
        for applicant_name in applicant_name.split():
            if len(applicant_name_part_one + applicant_name) < 70 and len(applicant_name_part_two) < 1:
                applicant_name_part_one = applicant_name_part_one + ' ' + applicant_name
            elif len(applicant_name_part_two + applicant_name) < 75:
                applicant_name_part_two = applicant_name_part_two + ' ' + applicant_name

        second_page_one_context.drawString(9.2 * cm, 22 * cm, applicant_name_part_one)
        if applicant_name_part_two:
            second_page_one_context.drawString(9.2 * cm, 21.7 * cm, applicant_name_part_two)

        biocide_trade_name_and_etc_ru = protocol.biocide_trade_name + '; ' + protocol.concentration + '; ' + \
                                        protocol.biocide.name_ru + '; ' + protocol.irritant_substance
        biocide_trade_name_and_etc_part_one = ''
        biocide_trade_name_and_etc_part_two = ''
        biocide_trade_name_and_etc_part_three = ''
        biocide_trade_name_and_etc_part_four = ''
        for biocide_trade_name_and_etc in biocide_trade_name_and_etc_ru.split():
            if len(biocide_trade_name_and_etc_part_one + biocide_trade_name_and_etc) < 50 and len(
                    biocide_trade_name_and_etc_part_two) < 1:
                biocide_trade_name_and_etc_part_one = biocide_trade_name_and_etc_part_one + ' ' + biocide_trade_name_and_etc
            elif len(biocide_trade_name_and_etc_part_two + biocide_trade_name_and_etc) < 50 and len(
                    biocide_trade_name_and_etc_part_three) < 1:
                biocide_trade_name_and_etc_part_two = biocide_trade_name_and_etc_part_two + ' ' + biocide_trade_name_and_etc
            elif len(biocide_trade_name_and_etc_part_three + biocide_trade_name_and_etc) < 50 and len(
                    biocide_trade_name_and_etc_part_four) < 1:
                biocide_trade_name_and_etc_part_three = biocide_trade_name_and_etc_part_three + ' ' + biocide_trade_name_and_etc
            elif len(biocide_trade_name_and_etc_part_four + biocide_trade_name_and_etc) < 55:
                biocide_trade_name_and_etc_part_four = biocide_trade_name_and_etc_part_four + ' ' + biocide_trade_name_and_etc
        second_page_one_context.drawString(10 * cm, 20.5 * cm, biocide_trade_name_and_etc_part_one)
        if biocide_trade_name_and_etc_part_two:
            second_page_one_context.drawString(10 * cm, 20.1 * cm, biocide_trade_name_and_etc_part_two)
        if biocide_trade_name_and_etc_part_three:
            second_page_one_context.drawString(10 * cm, 19.5 * cm, biocide_trade_name_and_etc_part_three)
        if biocide_trade_name_and_etc_part_four:
            second_page_one_context.drawString(10 * cm, 19.1 * cm, biocide_trade_name_and_etc_part_four)

        counter = 0
        y = 16
        z = 16
        w = 16

        for scope in protocol.scopes.all():
            counter += 1
            # first_page_one_context.drawString(1.8 * cm, y * cm, str(tbotd.ikr_shipment.fito_given_date))
            # first_page_one_context.drawString(1.7 * cm, y * cm, str(tbotd.ikr_shipment.info))
            # first_page_one_context.drawString(1.7 * cm, y * cm, str(tbotd.number))

            plant_type_part_parts_list = []
            plant_type_part = ''
            for plant_type in scope.plant_type_ru.split():
                if len(plant_type_part + plant_type) < 20:
                    plant_type_part = plant_type_part + plant_type + ' '
                else:
                    plant_type_part_parts_list.append(plant_type_part)
                    plant_type_part = plant_type + ' '

            if len(plant_type_part) <= 20:
                plant_type_part_parts_list.append(plant_type_part)  # do not remove this line never ever
            second_counter = 0
            for plant_type_part in plant_type_part_parts_list:
                second_counter += 1
                if second_counter == 1:
                    plant_type_part = f'{counter}. ' + plant_type_part
                second_page_one_context.drawString(3.1 * cm, y * cm, plant_type_part)
                y = y - 0.3
            y -= 0.2

            harmful_organisms_part_parts_list = []
            harmful_organisms_part = ''
            for harmful_organisms in scope.harmful_organisms_ru.split():
                if len(harmful_organisms_part + harmful_organisms) < 20:
                    harmful_organisms_part = harmful_organisms_part + harmful_organisms + ' '
                else:
                    harmful_organisms_part_parts_list.append(harmful_organisms_part)
                    harmful_organisms_part = harmful_organisms + ' '

            if len(harmful_organisms_part) <= 20:
                harmful_organisms_part_parts_list.append(harmful_organisms_part)  # do not remove this line never ever
            second_counter = 0
            for harmful_organisms_part in harmful_organisms_part_parts_list:
                second_counter += 1
                if second_counter == 1:
                    harmful_organisms_part = f'{counter}. ' + harmful_organisms_part
                    second_page_one_context.drawString(10.6 * cm, z * cm, f'{counter}. ' + str(scope.amount) + ' ' + str(
                        UNIT_CHOICES[scope.unit - 1][1]))
                second_page_one_context.drawString(6.7 * cm, z * cm, harmful_organisms_part)
                z = z - 0.3
            z -= 0.2

            scope_part_parts_list = []
            scope_part = ''
            for scope in scope.scope_ru.split():
                if len(scope_part + scope) < 35:
                    scope_part = scope_part + scope + ' '
                else:
                    scope_part_parts_list.append(scope_part)
                    scope_part = scope + ' '

            if len(scope_part) <= 35:
                scope_part_parts_list.append(scope_part)  # do not remove this line never ever
            second_counter = 0
            for scope_part in scope_part_parts_list:
                second_counter += 1
                if second_counter == 1:
                    scope_part = f'{counter}. ' + scope_part
                second_page_one_context.drawString(13.7 * cm, w * cm, scope_part)
                w = w - 0.3
            w -= 0.2

        second_page_one_context.drawString(10 * cm, 5.5 * cm, f'№ {protocol.biocide_registered_number}, ' + str(
            protocol.biocide_registered_date.strftime('%d-%m-%Y') if protocol.biocide_registered_date else ''))
        second_page_one_context.drawString(8.5 * cm, 4 * cm, str(protocol.expire_date.strftime('%d-%m-%Y')))
        second_page_one_context.drawString(12 * cm, 2.2 * cm, protocol.approved_by.name_ru if protocol.approved_by else '')
        second_page_one_context.drawImage(qrcode_image, 17.5 * cm, 1.7 * cm, width=55, height=55, mask='auto')
        second_page_one_context.save()
        second_packet.seek(0)

        for_second_page = PdfFileReader(second_packet)
        ikr_pdf_template = PdfFileReader(open("static/blanks/ppp_registration_protocol.pdf", "rb"))

        output = PdfFileWriter()

        first_page = ikr_pdf_template.getPage(0)
        first_page.mergePage(for_first_page.getPage(0))
        second_page = ikr_pdf_template.getPage(1)
        second_page.mergePage(for_second_page.getPage(0))
        output.addPage(first_page)
        output.addPage(second_page)

        output_stream = open("media/blanks/{}.pdf".format(file_name), "wb")
        output.write(output_stream)
        output_stream.close()

        new_ikr = f'blanks/{file_name}.pdf'  # look up file from media automatically
        if fs.exists(new_ikr):
            with fs.open(new_ikr) as pdf:
                response = HttpResponse(pdf, content_type='application/pdf')
                response['Content-Disposition'] = 'inline; filename="{}.pdf"'.format(file_name)
                os.remove(f'media/blanks/{file_name}.pdf')  # remove new_invoice after downloading
                return response
        else:
            return HttpResponseNotFound('The requested pdf was not found in our server.')


class DownloadListInExcelView(View):

    def get(self, request, *args, **kwargs):

        post = request.GET
        biocide_id = post.get('biocide_id')
        beginning_of_interval = post.get('beginning_of_interval')
        end_of_interval = post.get('end_of_interval')
        file_name = 'ppp_registration_protocol_(' + beginning_of_interval + '___' + end_of_interval + ')'

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
        columns = ['Рақами', 'Берилган санаси', 'Амал қилиш муддати', 'Давлат', 'Ташкилот номи', 'Ташкилот СТИР',
                   'Препарат шакли', 'Савдо номи', 'Рақами', 'Санаси', 'Концентрацияси',
                   'таъсир этувчи модда', 'Препаратдан фойдаланиладиган экин тури',
                   'Қайси зарарли организмга қарши ишлатилади', 'Сарф меъёри',
                   'Ишлатиш муддати, усули ва тавсия этилган чекловлар', 'ишлов тугалланади, кун', 'неча марта ишлатилади']

        # write column headers in sheet
        for col_num in range(len(columns)):
            ws.write(row_num, col_num, columns[col_num], font_style)

        # Sheet body, remaining rows
        font_style = xlwt.XFStyle()

        # get your data, from database or from a text file...

        if beginning_of_interval and end_of_interval and biocide_id:
            protocols = PPPRegistrationProtocol.objects.filter(given_date__gte=beginning_of_interval, given_date__lte=end_of_interval)

            if biocide_id != 'all':
                protocols = protocols.filter(biocide_id=biocide_id)

            for protocol in protocols:
                scopes = ''
                scopes = protocol.scopes.all()
                count = 0
                for scope in scopes:
                    count = count + 1
                    row_num = row_num + 1
                    if count == 1:
                        ws.write(row_num, 0, protocol.number, font_style)
                    ws.write(row_num, 1, protocol.given_date, font_style)
                    ws.write(row_num, 2, protocol.expire_date, font_style)
                    ws.write(row_num, 3, protocol.country.name_ru, font_style)
                    ws.write(row_num, 4, protocol.applicant_name, font_style)
                    ws.write(row_num, 5, protocol.applicant_tin, font_style)
                    ws.write(row_num, 6, protocol.biocide.code + protocol.biocide.name_uz, font_style)
                    ws.write(row_num, 7, protocol.biocide_trade_name, font_style)
                    ws.write(row_num, 8, protocol.biocide_registered_number, font_style)
                    ws.write(row_num, 9, protocol.biocide_registered_date, font_style)
                    ws.write(row_num, 10, protocol.concentration, font_style)
                    ws.write(row_num, 11, protocol.irritant_substance, font_style)
                    ws.write(row_num, 12, scope.plant_type_uz, font_style)
                    ws.write(row_num, 13, scope.harmful_organisms_uz, font_style)
                    ws.write(row_num, 14, scope.amount, font_style)
                    ws.write(row_num, 15, UNIT_CHOICES[scope.unit - 1][1], font_style)
                    ws.write(row_num, 16, scope.scope_uz, font_style)
                    ws.write(row_num, 17, scope.day, font_style)
                    ws.write(row_num, 18, scope.time, font_style)
        wb.save(response)
        return response