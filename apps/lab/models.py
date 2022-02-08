import datetime
from django.db import models
from django.db.models import Sum
from django.utils import timezone

from administration import statuses
from administration.models import Unit, Region, ContractPayment, Refund, Balance
from exim.models import IKRShipmentProduct
from invoice.models import InvoicePayment
from invoice.statuses import InvoiceServices
from lab.managers import IsApprovedManager


class LabChemicalReactive(models.Model):
    name = models.CharField(max_length=512, null=True)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    price = models.DecimalField(verbose_name='Цена', max_digits=10, decimal_places=2, default=0)
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.name)

    class Meta:
        db_table = 'lab_chemical_reactive'
        verbose_name = 'Lab Chemical Reactive'
        verbose_name_plural = 'Lab Chemical Reactive'
        ordering = ('-id',)


class LabDisposable(models.Model):
    name = models.CharField(max_length=512, null=True)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    price = models.DecimalField(verbose_name='Цена', max_digits=10, decimal_places=2, default=0)
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.name)

    class Meta:
        db_table = 'lab_disposable'
        verbose_name = 'Lab Disposable'
        verbose_name_plural = 'Lab Disposables'
        ordering = ('-id',)


class LabTestMethod(models.Model):
    name = models.CharField(max_length=512)
    normative_document = models.CharField(max_length=512)
    expertise_type = models.IntegerField(choices=statuses.ExpertiseType.CHOICES)
    accreditation_type = models.CharField(max_length=16)
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.name)

    @property
    def accreditation(self):
        if self.accreditation_type == 'snas':
            return 'S-407'
        elif self.accreditation_type == 'uzakk':
            return "O'ZAK.SL.0110"
        else:
            return '---'


    class Meta:
        db_table = 'lab_test_method'
        verbose_name = 'Lab Test Method'
        verbose_name_plural = 'Lab Test Methods'
        ordering = ('-id',)


class ImportShortcut(models.Model):
    number = models.CharField(max_length=15, unique=True, null=True, verbose_name='№')
    ikr = models.ForeignKey('exim.IKR', on_delete=models.CASCADE, related_name='lab_shortcuts')
    point = models.ForeignKey('administration.Point', on_delete=models.CASCADE, verbose_name='Точка')
    registerer = models.ForeignKey('administration.User', on_delete=models.CASCADE, verbose_name='Registerer')
    added_at = models.DateTimeField(auto_now_add=True, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.number)

    # def save(self, *args, **kwargs):
    #     if not self.pk:
    #         super(ImportShortcut, self).save()
    #         self.number = 'ML-I-' + str(
    #             int(datetime.datetime.now().strftime('%y')) * 100000000 + self.pk)
    #         self.save()
    #     else:
    #         super(ImportShortcut, self).save()

    class Meta:
        db_table = 'import_shortcut'
        verbose_name = 'Import Shortcut'
        verbose_name_plural = 'Import Shortcut'
        ordering = ('-id',)

        permissions = (
            # republic
            ('list_republic_import_shortcut', f'Can list republic {verbose_name}'),
            ('view_republic_import_shortcut', f'Can view republic {verbose_name}'),
            ('add_republic_import_shortcut', f'Can Add republic {verbose_name}')
        )


class ImportShortcutProduct(models.Model):
    name = models.CharField(max_length=128, null=True, verbose_name='Name')
    import_shortcut = models.ForeignKey(ImportShortcut, on_delete=models.CASCADE, related_name='products')
    shipment_product = models.OneToOneField(IKRShipmentProduct, on_delete=models.CASCADE,
                                            related_name='shipment_product')
    number_of_examples = models.IntegerField(null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.name)

    @property
    def hs_code(self):
        return self.shipment_product.ikr_product.hs_code

    class Meta:
        db_table = 'import_shortcut_product'
        verbose_name = 'Import Shortcut Product'
        verbose_name_plural = 'Import Shortcut Products'
        ordering = ('-id',)


class ImportProtocol(models.Model):
    number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    accreditation_number = models.CharField(max_length=50, null=True, blank=True)
    accreditation_given_date = models.DateField(null=True, blank=True)
    given_date = models.DateField(verbose_name='Выдано', null=True, blank=True)
    fsses_given_dates = models.TextField(null=True, blank=True)
    number_of_examples = models.IntegerField(null=True, blank=True)
    shortcut = models.OneToOneField(ImportShortcut, on_delete=models.CASCADE, related_name='protocol')
    point = models.ForeignKey('administration.Point', on_delete=models.CASCADE, verbose_name='Точка')
    inspection_general = models.ForeignKey('administration.User', on_delete=models.CASCADE,
                                           related_name='inspection_general_import_protocols', null=True, blank=True)
    registrar = models.ForeignKey('administration.User', on_delete=models.CASCADE, verbose_name='Registerer',
                                  related_name='registrar_import_protocols')
    head_of_lab = models.ForeignKey('administration.User', on_delete=models.CASCADE, related_name='head_of_lab')
    conclusion = models.TextField(null=True, blank=True, verbose_name='Тело сообщения')
    payment_amount = models.DecimalField(verbose_name='Сумма платежа', max_digits=10, decimal_places=2, default=0)
    is_approved = models.BooleanField(default=False)
    stamp_name = models.CharField(max_length=50, null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True)

    all_objects = models.Manager()
    objects = IsApprovedManager()

    def __str__(self):
        return str(self.number)

    @property
    def shortcut_number(self):
        return str(self.shortcut.number)

    @property
    def products(self):
        return self.shortcut.products.order_by('name').distinct('name')

    @property
    def balance(self):
        # start checking balance
        first_day_of_month = '2022-01-01'
        region = Region.objects.get(pk=15)
        tin = self.shortcut.ikr.importer_tin
        invoices_payments = InvoicePayment.objects.confirmed().filter(invoice__applicant_tin=tin,
                                                                      invoice__region=region,
                                                                      payment_date__gte=first_day_of_month)
        contract_payments = ContractPayment.objects.filter(organization__tin=tin, region=region,
                                                           payment_date__gte=first_day_of_month)
        refunds = Refund.objects.filter(organization__tin=tin, region=region,
                                        refunded_date__gte=first_day_of_month)
        balances = Balance.objects.filter(organization__tin=tin, month=first_day_of_month, region=region)

        service_amount = 0
        import_protocols = ImportProtocol.objects.filter(point__region=region, shortcut__ikr__importer_tin=tin,
                                                         given_date__gte=first_day_of_month).order_by(
            '-given_date')
        balance = balances.filter(service_type=InvoiceServices.LAB).first()
        if balance:
            current_balance = balance.amount
        else:
            current_balance = 0

        invoice_amount = \
            invoices_payments.filter(invoice__service_type=InvoiceServices.LAB).aggregate(Sum('payment_amount'))[
                'payment_amount__sum']
        if invoice_amount:
            current_balance = current_balance + invoice_amount

        contract_payment_amount = \
            contract_payments.filter(service_type=InvoiceServices.LAB).aggregate(Sum('payment_amount'))[
                'payment_amount__sum']
        if contract_payment_amount:
            current_balance = current_balance + contract_payment_amount

        refund_amount = refunds.filter(service_type=InvoiceServices.LAB).aggregate(Sum('amount'))['amount__sum']
        if refund_amount:
            current_balance = current_balance - refund_amount
        if import_protocols:
            service_amount = import_protocols.aggregate(Sum('payment_amount'))['payment_amount__sum']
        current_balance = current_balance - service_amount
        # end checking balance
        return current_balance - self.payment_amount

    @property
    def can_paid(self):
        return True if self.balance > 0 else False

    # def save(self, *args, **kwargs):
    #     if not self.pk:
    #         super(ImportProtocol, self).save()
    #         self.number = 'ML-I-' + str(
    #             int(datetime.datetime.now().strftime('%y')) * 100000000 + self.pk)
    #         self.save()
    #     else:
    #         super(ImportProtocol, self).save()

    class Meta:
        db_table = 'import_protocol'
        verbose_name = 'Import Protocol'
        verbose_name_plural = 'Import Protocol'
        ordering = ('-updated_at',)

        permissions = (
            # republic
            ('list_republic_import_protocol', f'Can list republic {verbose_name}'),
            ('view_republic_import_protocol', f'Can view republic {verbose_name}'),
            ('add_republic_import_protocol', f'Can Add republic {verbose_name}')
        )


class ImportProtocolConclusion(models.Model):
    import_protocol = models.ForeignKey(ImportProtocol, on_delete=models.CASCADE, related_name='conclusions')
    expertise_number = models.CharField(max_length=10, verbose_name='№', null=True, blank=True)
    conclusion = models.TextField(verbose_name='Тело сообщения', null=True, blank=True)
    expert = models.ForeignKey('administration.User', on_delete=models.CASCADE, verbose_name='Expert', null=True, blank=True)
    expertise_type = models.IntegerField(choices=statuses.ExpertiseType.CHOICES)
    is_approved = models.BooleanField(default=False)  # TODO Before release product mode, make True and migrate then make False and migrate
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        if self.import_protocol.number:
            return str(self.import_protocol.number)
        else:
            return str(self.pk)

    @property
    def shortcut(self):
        return self.import_protocol.shortcut

    class Meta:
        db_table = 'import_protocol_conclusion'
        verbose_name = 'Import Protocol Conclusion'
        verbose_name_plural = 'Import Protocol Conclusions'
        ordering = ('-id',)

        permissions = (
            ('list_import_protocol_conclusion', f'Can list {verbose_name}'),

            # expert
            ('add_entomology_import_protocol_conclusion', f'Can Add {verbose_name} as Энтомолог'),
            ('add_phytopathology_import_protocol_conclusion', f'Can Add {verbose_name} as Фитопотолог'),
            ('add_gerbolog_import_protocol_conclusion', f'Can Add {verbose_name} as Герболог'),
            ('add_bacteriologist_import_protocol_conclusion', f'Can Add {verbose_name} as Бактериолог'),
            ('add_helminthologist_import_protocol_conclusion', f'Can Add {verbose_name} as Гельминтолог'),
            ('add_virologist_import_protocol_conclusion', f'Can Add {verbose_name} as Вирусолог'),
            ('add_mikolog_import_protocol_conclusion', f'Can Add {verbose_name} as Миколог'),
        )


class UsedChemicalReactive(models.Model):
    import_protocol_conclusion = models.ForeignKey(ImportProtocolConclusion, on_delete=models.CASCADE, related_name='used_chemical_reactives')
    lab_chemical_reactive = models.ForeignKey(LabChemicalReactive, on_delete=models.CASCADE)
    number_of_examples = models.IntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=3)
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.amount)

    class Meta:
        db_table = 'used_chemical_reactive'
        verbose_name = 'Used Chemical Reactive'
        verbose_name_plural = 'Used Chemical Reactive'
        ordering = ('-id',)


class UsedDisposable(models.Model):
    import_protocol_conclusion = models.ForeignKey(ImportProtocolConclusion, on_delete=models.CASCADE, related_name='used_disposables')
    lab_disposable = models.ForeignKey(LabDisposable, on_delete=models.CASCADE)
    number_of_examples = models.IntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=3)
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.amount)

    class Meta:
        db_table = 'used_disposable'
        verbose_name = 'Used Disposable'
        verbose_name_plural = 'Used Disposables'
        ordering = ('-id',)


class ImplementedLabTestMethod(models.Model):
    import_protocol_conclusion = models.ForeignKey(ImportProtocolConclusion, on_delete=models.CASCADE, related_name='implemented_lab_test_methods')
    lab_test_method = models.ForeignKey(LabTestMethod, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.lab_test_method.name)

    class Meta:
        db_table = 'implemented_lab_test_method'
        verbose_name = 'Implemented Lab Test Method'
        verbose_name_plural = 'Implemented Lab Test Methods'
        ordering = ('-id',)
