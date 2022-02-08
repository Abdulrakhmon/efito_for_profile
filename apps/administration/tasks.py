import os
import datetime
import calendar

import xlwt
from django.db.models import Sum, Prefetch
from xlwt import Workbook

from administration.models import Balance, Organization, ContractPayment, Refund, Region, Message, User
from core.settings import BASE_DIR
from fumigation.models import CertificateOfDisinfestation

from exim.models import LocalFSS
from invoice.models import InvoicePayment

from celery import shared_task
from celery.task import periodic_task
from celery.utils.log import get_task_logger
from administration.models import IntegrationData, Region
from exim.models import ExportFSS, IKR, AKD
from invoice.statuses import InvoiceServices
from lab.models import ImportProtocol

logger = get_task_logger(__name__)


@periodic_task(run_every=datetime.timedelta(minutes=5), name="synchronize_integration_data")
def synchronize_integration_data():
    errors = []
    try:
        IntegrationData.send_integration_data()
    except Exception as e:
        errors.append(str(e))
    if errors:
        return errors
    return 'success'


@shared_task
def celery_task(chosen_date, region_pk, service_id, user_id):
    chosen_date = datetime.datetime.strptime(chosen_date, '%Y-%m')
    chosen_date_year = chosen_date.year
    chosen_date_month = chosen_date.month
    region = Region.objects.get(pk=region_pk)
    service = InvoiceServices.dictionary_ru[service_id]
    file_name = InvoiceServices.dictionary[service_id] + '_balance' + '_for_' + region.name_en + '_' + str(
        chosen_date_month) + '_' + str(chosen_date_year)
    file_name = file_name.replace(' ', '_')
    first_day_of_month = '2022-01-01'
    # first_day_of_month = datetime.date(chosen_date_year, chosen_date_month, 1)
    day, num_days = calendar.monthrange(chosen_date_year, chosen_date_month)
    last_day_of_month = datetime.date(chosen_date_year, chosen_date_month, num_days)
    # organizations = organizations.balances.filter(region=region, service_type=service_id)
    wb = Workbook()

    ws = wb.add_sheet("sheet1")

    # Sheet header, first row
    row_num = 0

    font_style = xlwt.XFStyle()
    # headers are bold
    font_style.font.bold = True

    # column header names, you can use your own headers here
    columns = ['Контрагент', 'ИНН', 'Дебет на начало', 'Кредит на начало', 'Дебет за период', 'Кредит за период',
               'Дебет на конец', 'Кредит на конец', 'Услуги']

    # write column headers in sheet
    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num], font_style)

    # Sheet body, remaining rows
    font_style = xlwt.XFStyle()

    # get your data, from database or from a text file...
    row_num = 0
    organizations = Organization.objects.prefetch_related(Prefetch('balances', queryset=Balance.objects.filter(
        month=first_day_of_month, region=region, service_type=service_id)))
    for organization in organizations:
        tin = organization.tin
        balances = organization.balances.all()
        invoices_payments = InvoicePayment.objects.confirmed().filter(invoice__applicant_tin=tin,
                                                                      invoice__region=region,
                                                                      payment_date__gte=first_day_of_month,
                                                                      payment_date__lte=last_day_of_month,
                                                                      invoice__service_type=service_id)
        contract_payments = ContractPayment.objects.filter(organization=organization, region=region,
                                                           payment_date__gte=first_day_of_month,
                                                           payment_date__lte=last_day_of_month,
                                                           service_type=service_id)
        refunds = Refund.objects.filter(organization=organization, region=region, service_type=service_id,
                                        refunded_date__gte=first_day_of_month, refunded_date__lte=last_day_of_month)
        balance = 0
        invoice_amount = 0
        amount = 0
        refund_amount = 0
        contract_payment_amount = 0
        service_amount = 0
        if service_id == InvoiceServices.IKR:
            ikrs = IKR.objects.filter(importer_tin=tin, given_date__gte=first_day_of_month,
                                      given_date__lte=last_day_of_month)
            balance = balances.first()
            if balance:
                balance = balance.amount
                amount = balance
            else:
                amount = 0
                balance = 0
            invoice_amount = invoices_payments.aggregate(Sum('payment_amount'))['payment_amount__sum']
            if invoice_amount:
                amount = amount + invoice_amount
            else:
                invoice_amount = 0

            contract_payment_amount = contract_payments.aggregate(Sum('payment_amount'))['payment_amount__sum']
            if contract_payment_amount:
                amount = amount + contract_payment_amount
            else:
                contract_payment_amount = 0

            refund_amount = refunds.aggregate(Sum('amount'))['amount__sum']
            if refund_amount:
                amount = amount - refund_amount
            else:
                refund_amount = 0
            if ikrs:
                service_amount = ikrs.aggregate(Sum('payment_amount'))['payment_amount__sum']
            amount = amount - service_amount
        elif service_id == InvoiceServices.TBOTD:
            akds = AKD.objects.filter(importer_tin=tin, given_date__gte=first_day_of_month,
                                      given_date__lte=last_day_of_month)
            akds = akds.filter(tbotd__ikr_shipment__ikr__point__region=region)
            balance = balances.first()
            if balance:
                balance = balance.amount
                amount = balance
            else:
                balance = 0
                amount = 0
            invoice_amount = invoices_payments.aggregate(Sum('payment_amount'))[
                'payment_amount__sum']
            if invoice_amount:
                amount = amount + invoice_amount
            else:
                invoice_amount = 0

            contract_payment_amount = contract_payments.aggregate(Sum('payment_amount'))['payment_amount__sum']
            if contract_payment_amount:
                amount = amount + contract_payment_amount
            else:
                contract_payment_amount = 0

            refund_amount = refunds.aggregate(Sum('amount'))['amount__sum']
            if refund_amount:
                amount = amount - refund_amount
            else:
                refund_amount = 0

            if akds:
                service_amount = akds.aggregate(Sum('payment_amount'))['payment_amount__sum']
            amount = amount - service_amount
        elif service_id == InvoiceServices.FUMIGATION:
            certificates_of_disinfestation = CertificateOfDisinfestation.objects.filter(region=region,
                                                                                        organization_tin=tin,
                                                                                        given_date__gte=first_day_of_month,
                                                                                        given_date__lte=last_day_of_month)
            balance = balances.first()
            if balance:
                balance = balance.amount
                amount = balance
            else:
                balance = 0
                amount = 0
            invoice_amount = invoices_payments.aggregate(Sum('payment_amount'))['payment_amount__sum']
            if invoice_amount:
                amount = amount + invoice_amount
            else:
                invoice_amount = 0

            contract_payment_amount = contract_payments.aggregate(Sum('payment_amount'))['payment_amount__sum']
            if contract_payment_amount:
                amount = amount + contract_payment_amount
            else:
                contract_payment_amount = 0

            refund_amount = refunds.aggregate(Sum('amount'))['amount__sum']
            if refund_amount:
                amount = amount - refund_amount
            else:
                refund_amount = 0

            if certificates_of_disinfestation:
                service_amount = certificates_of_disinfestation.aggregate(Sum('total_price'))['total_price__sum']
            amount = amount - service_amount
        elif service_id == InvoiceServices.FSS:
            export_fsses = ExportFSS.all_objects.filter(region=region, exporter_tin=tin,
                                                        given_date__gte=first_day_of_month,
                                                        given_date__lte=last_day_of_month)
            balance = balances.first()
            if balance:
                balance = balance.amount
                amount = balance
            else:
                balance = 0
                amount = 0

            invoice_amount = invoices_payments.aggregate(Sum('payment_amount'))['payment_amount__sum']
            if invoice_amount:
                amount = amount + invoice_amount
            else:
                invoice_amount = 0

            contract_payment_amount = contract_payments.aggregate(Sum('payment_amount'))['payment_amount__sum']
            if contract_payment_amount:
                amount = amount + contract_payment_amount
            else:
                contract_payment_amount = 0

            refund_amount = refunds.aggregate(Sum('amount'))['amount__sum']
            if refund_amount:
                amount = amount - refund_amount
            else:
                refund_amount = 0

            if export_fsses:
                service_amount = export_fsses.aggregate(Sum('payment_amount'))['payment_amount__sum']
            amount = amount - service_amount
        elif service_id == InvoiceServices.LocalFSS:
            local_fsses = LocalFSS.objects.filter(sender_region=region, applicant_tin=tin,
                                                  given_date__gte=first_day_of_month, given_date__lte=last_day_of_month)
            balance = balances.first()
            if balance:
                balance = balance.amount
                amount = balance
            else:
                balance = 0
                amount = 0

            invoice_amount = invoices_payments.aggregate(Sum('payment_amount'))['payment_amount__sum']
            if invoice_amount:
                amount = amount + invoice_amount
            else:
                invoice_amount = 0

            contract_payment_amount = contract_payments.aggregate(Sum('payment_amount'))['payment_amount__sum']
            if contract_payment_amount:
                amount = amount + contract_payment_amount
            else:
                contract_payment_amount = 0

            refund_amount = refunds.aggregate(Sum('amount'))['amount__sum']
            if refund_amount:
                amount = amount - refund_amount
            else:
                refund_amount = 0

            if local_fsses:
                service_amount = local_fsses.aggregate(Sum('payment_amount'))['payment_amount__sum']
            amount = amount - service_amount
        elif service_id == InvoiceServices.LAB:
            import_protocols = ImportProtocol.objects.filter(point__region=region, shortcut__ikr__importer_tin=tin,
                                                  given_date__gte=first_day_of_month, given_date__lte=last_day_of_month)
            balance = balances.first()
            if balance:
                balance = balance.amount
                amount = balance
            else:
                balance = 0
                amount = 0

            invoice_amount = invoices_payments.aggregate(Sum('payment_amount'))['payment_amount__sum']
            if invoice_amount:
                amount = amount + invoice_amount
            else:
                invoice_amount = 0

            contract_payment_amount = contract_payments.aggregate(Sum('payment_amount'))['payment_amount__sum']
            if contract_payment_amount:
                amount = amount + contract_payment_amount
            else:
                contract_payment_amount = 0

            refund_amount = refunds.aggregate(Sum('amount'))['amount__sum']
            if refund_amount:
                amount = amount - refund_amount
            else:
                refund_amount = 0

            if import_protocols:
                service_amount = import_protocols.aggregate(Sum('payment_amount'))['payment_amount__sum']
            amount = amount - service_amount
        if balance == 0 and service_amount == 0 and amount == 0:
            pass
        else:
            row_num = row_num + 1
            ws.write(row_num, 0, organization.name, font_style)
            ws.write(row_num, 1, tin, font_style)
            if balance > 0:
                ws.write(row_num, 2, '-', font_style)
                ws.write(row_num, 3, balance, font_style)
            else:
                ws.write(row_num, 2, balance, font_style)
                ws.write(row_num, 3, '-', font_style)
            ws.write(row_num, 4, service_amount, font_style)
            ws.write(row_num, 5, invoice_amount + contract_payment_amount - refund_amount, font_style)
            if amount > 0:
                ws.write(row_num, 6, '-', font_style)
                ws.write(row_num, 7, amount, font_style)
            else:
                ws.write(row_num, 6, amount, font_style)
                ws.write(row_num, 7, '-', font_style)
            ws.write(row_num, 8, service, font_style)

    file_path = 'media/balance/{}.xls'.format(file_name)
    wb.save(os.path.join(BASE_DIR, file_path))
    Message.objects.create(sender=User.objects.get(username='a201283204'), receiver=User.objects.get(pk=user_id), title=f'{service} сальдо за {chosen_date_month}-{chosen_date_year}', body=f'<a href="/{file_path}"><i class="fas fa-file"></i></a>')
    return True