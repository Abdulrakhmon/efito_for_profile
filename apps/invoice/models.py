import datetime

from administration.statuses import OrganizationType
from .managers import InvoicePaymentManager, ActiveInvoicesManager
from .statuses import InvoicePaymentStatuses
from django.contrib.postgres.fields import JSONField
from django.db import models
from administration.models import User, Region
from invoice.statuses import InvoiceServices


class Invoice(models.Model):
    region = models.ForeignKey(Region, on_delete=models.DO_NOTHING, verbose_name='Код региона заявителя')
    number = models.CharField(max_length=20, verbose_name='Номер Оферта', unique=True, null=True)
    given_date = models.DateField(auto_now_add=True, verbose_name='Дата выдачи')
    service_type = models.IntegerField(choices=InvoiceServices.CHOICES, verbose_name='Service Type')
    number_of_services = models.IntegerField(verbose_name='Количество услуг')
    remainder_number_of_services = models.IntegerField(verbose_name='Оставшееся количество услуг')
    payment_amount = models.DecimalField(verbose_name='Сумма платежа', max_digits=15, decimal_places=2)
    paid_amount = models.DecimalField(default=0, verbose_name='Оплаченное количество', max_digits=15, decimal_places=2)
    is_paid = models.BooleanField(default=False, verbose_name='Paid')
    applicant_organization = models.CharField(verbose_name='Организация', max_length=128, null=True)
    applicant_tin = models.CharField(verbose_name='ИНН/ПИНФЛ заявителя', max_length=15, null=True)
    applicant_fullname = models.CharField(verbose_name='ФИО заявителя', max_length=60, null=True)
    applicant_phone = models.CharField(verbose_name='Телефонный номер', max_length=9, null=True)
    inspection_general = models.CharField(verbose_name='Директор', max_length=50, default='')
    organization_type = models.IntegerField(choices=OrganizationType.CHOICES, verbose_name='Service Type',
                                            default=OrganizationType.OTHERS)
    organization_bank_id = models.CharField(verbose_name='МФО', max_length=10, null=True, blank=True)
    organization_bank_name = models.CharField(max_length=500, null=True, blank=True)
    organization_bank_account = models.CharField(max_length=27, null=True, verbose_name='лицевой счет', blank=True)
    organization_mfo = models.CharField(max_length=10, null=True, blank=True)
    organization_oked = models.CharField(max_length=10, null=True, blank=True)
    organization_director = models.CharField(max_length=50, null=True, blank=True)
    organization_accountant = models.CharField(max_length=50, null=True, blank=True)
    organization_address = models.CharField(max_length=500, null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    objects = models.Manager()  # The default manager.
    active_objects = ActiveInvoicesManager()  # The default manager.
    bank_mfo = '00014'
    # tin = '201122919'
    treasury_account = '23402000300100001010'
    treasury_name = 'Молия Вазирлиги Ягона Газна хисобвараги'
    treasury_tin = '201122919'

    def __str__(self):
        return str(self.number)

    @property
    def expire_date(self):
        return '31.12.' + str(self.given_date.strftime("%Y"))\

    @property
    def organization_director_short_name(self):
        name = self.organization_director.split(' ')
        return name[0][0] + '.' + name[1]

    @property
    def service_type_name(self):
        return InvoiceServices.dictionary.get(self.service_type)

    @property
    def remaining_amount(self):
        return self.payment_amount - self.paid_amount

    def save(self, *args, **kwargs):
        if self.pk:
            self.is_paid = self.payment_amount <= self.paid_amount
        super(Invoice, self).save()

    class Meta:
        verbose_name = 'Оферта'
        verbose_name_plural = 'Оферта'
        db_table = 'invoice'
        get_latest_by = 'added_at'
        ordering = ('-added_at',)
        default_permissions = ()

        permissions = (
            # republic
            ('list_republic_invoice', f'Can list republic {verbose_name}'),
            ('view_republic_invoice', f'Can View republic {verbose_name}'),

            # region
            ('list_region_invoice', f'Can list region {verbose_name}'),
            ('view_region_invoice', f'Can View region {verbose_name}'),

            # accountant
            # ('delete_accountant_invoice', f'Can delete accountant {verbose_name}'),
            # ('change_accountant_invoice', f'Can change accountant {verbose_name}')
        )


class InvoicePayment(models.Model):
    number = models.CharField(max_length=20, verbose_name='Номер', unique=True, null=True)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments',
                                verbose_name='Invoice')
    order_number = models.CharField(max_length=128, verbose_name='Платёжны поручения №')
    payment_amount = models.DecimalField(verbose_name='Сумма платежа', max_digits=15, decimal_places=2)
    payment_date = models.DateField(verbose_name='Дата оплаты')
    accountant = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Бухгалтер')
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    extra_data = JSONField(null=True, blank=True)
    status = models.IntegerField(choices=InvoicePaymentStatuses.choices, default=InvoicePaymentStatuses.not_confirmed)

    objects = InvoicePaymentManager()

    def __str__(self):
        return str(self.order_number)

    @property
    def payer_name(self):
        payer_name = ''
        if self.extra_data:
            if self.extra_data.get('payer'):
                if self.extra_data.get('payer').get('name'):
                    payer_name = self.extra_data.get('payer').get('name')

            if self.extra_data.get('purpose'):
                if self.extra_data.get('purpose').get('text'):
                    if payer_name:
                        payer_name = payer_name + " || "
                    payer_name = payer_name + self.extra_data.get('purpose').get('text')
        return payer_name

    @property
    def generate_number(self):
        return int(datetime.datetime.now().strftime('%y')) * 1000000000 + int(
            self.invoice.region.pk) * 10000000 + self.pk

    def save(self, *args, **kwargs):
        if not self.pk:
            super(InvoicePayment, self).save()
            self.number = self.generate_number  # last two digits of year + region_id + pk of invoice
            self.save()
        else:
            if not self.number:
                self.number = self.generate_number
            super(InvoicePayment, self).save()

    class Meta:
        verbose_name = 'Оплата оферта'
        verbose_name_plural = 'Оплати оферта'
        db_table = 'invoice_payment'
        get_latest_by = 'added_at'
        default_permissions = ()
        permissions = (
            # republic
            ('add_republic_invoice_payment', f'Can add republic {verbose_name}'),
            # region
            ('add_region_invoice_payment', f'Can add region {verbose_name}'),
        )


class InvoiceProvidedService(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='provided_services',
                                verbose_name='Provided Services')
    invoice_number = models.CharField(max_length=20, verbose_name='Номер Оферта')
    number = models.CharField(max_length=128, verbose_name='Номер предоставляемой услуги')
    provider = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Поставщик услуг')
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')

    def __str__(self):
        return str(self.number)

    class Meta:
        verbose_name = 'Provided Service'
        verbose_name_plural = 'Provided Services'
        db_table = 'provided_service'
        get_latest_by = 'added_at'
        ordering = ('added_at',)
        default_permissions = ()

        permissions = (
            # region
            ('add_region_provided_service', f'Can Add Region Provided Service {verbose_name}'),

            ('add_point_provided_service', f'Can Add Point Provided Service {verbose_name}'),
        )


class InvoiceRefund(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='refunds', verbose_name='Invoice')
    order_number = models.CharField(max_length=128, verbose_name='Возврат поручения №')
    refund_amount = models.DecimalField(verbose_name='Сумма refund', max_digits=10, decimal_places=2, null=True)
    refund_date = models.DateField(verbose_name='Дата оплаты')
    accountant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='Бухгалтер', verbose_name='Бухгалтер')
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')

    def __str__(self):
        return str(self.order_number)

    class Meta:
        verbose_name = 'Возврат оферта'
        verbose_name_plural = 'Возврат оферта'
        db_table = 'invoice_refund'
        get_latest_by = 'added_at'
        default_permissions = ()
        permissions = (
            # republic
            ('add_republic_invoice_refund', f'Can add republic {verbose_name}'),
            # region
            ('add_region_invoice_refund', f'Can add region {verbose_name}'),
        )
