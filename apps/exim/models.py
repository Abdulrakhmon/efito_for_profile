import base64
import datetime
import locale
import os
import re
import uuid
import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.postgres.fields import JSONField
from django.core.files.storage import FileSystemStorage
from django.db.models import Sum
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.db import models
from django.urls import reverse
from django.utils.safestring import mark_safe
from requests.auth import HTTPBasicAuth

from administration.models import Country, User, Unit, Point, Region, HSCode, District, SMSNotification, APIUser, \
    Integration, IntegrationData, ContractPayment, Refund, Balance
from core.settings import TIME_FOR_SHIPMENT, SMS_NOTIFICATION_ORIGINATOR, SMS_NOTIFICATION_API_BASE_URL, \
    TIME_FOR_TEMPORARILY_STOPPED_SHIPMENT
from exim.managers import IKRShipmentManager, IKRShipmentProductManager, IsApprovedManager, \
    IsUnapprovedManager, IsActiveManager, IsIKRUnapprovedManager
from administration.statuses import IKRShipmentStatuses, Languages, TransPortTypes, APIAction, \
    WrongAKDErrorTypes, BlankTypes, CustomerType, SMSNotificationPurposes, SMSNotificationStatuses, ImpExpLocChoices, \
    ApplicationStatuses, ApplicationTypes, TemporarilyStoppedShipmentStatuses, IntegratedDataType
from exim.statuses import SynchronisationStatus
from fumigation.models import CertificateOfDisinfestation
from invoice.models import InvoicePayment
from invoice.statuses import InvoiceServices


class IKRApplication(models.Model):
    request_number = models.CharField(unique=True, max_length=30, verbose_name='Номер заявки')
    request_date = models.DateField(verbose_name='Дата заявления', null=True, blank=True)
    applicant_type = models.IntegerField(choices=CustomerType.CHOICES, verbose_name='Налогоплательщик', null=True,
                                         blank=True)
    applicant_tin = models.CharField(verbose_name='ИНН', max_length=15, null=True, blank=True)
    applicant_name = models.CharField(max_length=155, verbose_name='Наименование заявителя/организации', null=True,
                                      blank=True)
    applicant_representative_name = models.CharField(max_length=155, verbose_name='Ф.И.О. руководителя', null=True,
                                                     blank=True)
    applicant_region = models.ForeignKey(Region, on_delete=models.DO_NOTHING, verbose_name='регион', null=True,
                                         blank=True, related_name='ikr_applicants')
    applicant_address = models.CharField(max_length=300, verbose_name='Адрес', null=True, blank=True)
    applicant_phone = models.CharField(max_length=35, verbose_name='Телефон', null=True, blank=True)
    applicant_fax = models.CharField(max_length=35, verbose_name='Факс', null=True, blank=True)
    importer_type = models.IntegerField(choices=CustomerType.CHOICES, verbose_name='Налогоплательщик', null=True,
                                        blank=True)
    importer_tin = models.CharField(verbose_name='ИНН', max_length=15, null=True, blank=True)
    importer_name = models.CharField(max_length=155, verbose_name='Наименование импортера/организации', null=True,
                                     blank=True)
    importer_representative_name = models.CharField(max_length=155, verbose_name='Ф.И.О. руководителя', null=True,
                                                    blank=True)
    importer_region = models.ForeignKey(Region, on_delete=models.DO_NOTHING, related_name='ikr_importers', null=True,
                                        blank=True, verbose_name='регион')
    importer_address = models.CharField(max_length=300, verbose_name='Адрес', null=True, blank=True)
    importer_phone_number = models.CharField(max_length=35, verbose_name='Телефон', null=True, blank=True)
    importer_fax = models.CharField(max_length=35, verbose_name='Факс', null=True, blank=True)
    exporter_organization_name = models.CharField(max_length=155, verbose_name='Наименование экспортера', null=True,
                                                  blank=True)
    exporter_country = models.ForeignKey(Country, on_delete=models.CASCADE, verbose_name='Экспортирующая страна',
                                         related_name='ikrs_in_application', null=True, blank=True)
    exporter_address = models.CharField(max_length=300, verbose_name='Адрес и наименование места производства',
                                        null=True, blank=True)
    importer_contract_number = models.CharField(max_length=200, verbose_name='Номер импортного контракта', null=True,
                                                blank=True)
    importer_contract_date = models.DateField(verbose_name='Дата импортного контракта', null=True, blank=True)
    transit_exporter_country = models.ForeignKey(Country, on_delete=models.CASCADE, verbose_name='Транзит (от)',
                                                 related_name='transit_exporter_country_in_application', null=True,
                                                 blank=True)
    transit_importer_country = models.ForeignKey(Country, on_delete=models.CASCADE, verbose_name='Транзит (до)',
                                                 related_name='transit_importer_country_in_application', null=True,
                                                 blank=True)
    transport_method = models.IntegerField(choices=TransPortTypes.choices, verbose_name='Метод транспортировки',
                                           null=True, blank=True)
    point = models.ForeignKey(Point, on_delete=models.CASCADE, null=True, blank=True,
                              verbose_name='Наименование пункта назначения (место растаможки груза)')
    entering_point_in_transit = models.ForeignKey(Point, on_delete=models.CASCADE, null=True, blank=True,
                                                  verbose_name='Транзит (от)', related_name='entering_point_in_transit')
    leaving_point_in_transit = models.ForeignKey(Point, on_delete=models.CASCADE, null=True, blank=True,
                                                 verbose_name='Транзит (до)', related_name='leaving_point_in_transit')
    expected_entering_date_in_transit = models.DateField(verbose_name='Ожидаемый срок транзита: (с даты)', null=True,
                                                         blank=True)
    expected_leaving_date_in_transit = models.DateField(verbose_name='Ожидаемый срок транзита: (по дату)', null=True,
                                                        blank=True)
    route = models.CharField(max_length=4000, verbose_name='Маршрут транспортировки (пункт погранперехода)', null=True,
                             blank=True)
    expected_date_of_sending_products = models.DateField(verbose_name='Ожидаемый срок отправки материала', null=True,
                                                         blank=True)
    expected_date_of_arrivaling_products = models.DateField(verbose_name='Ожидаемый срок прибытия материала', null=True,
                                                            blank=True)
    used_place_of_products = models.CharField(max_length=4000, verbose_name='Место использования материалов', null=True)
    used_purpose_of_products = models.CharField(max_length=4000, verbose_name='Цель использования материалов',
                                                null=True)
    certificate_of_disinfestation_number = models.CharField(max_length=1000,
                                                            verbose_name='Цель использования материалов', null=True)
    is_transit = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_paid = models.BooleanField(default=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Инспектор', null=True, blank=True)
    status = models.IntegerField(choices=ApplicationStatuses.CHOICES, default=ApplicationStatuses.ONE_ZERO_ZERO,
                                 verbose_name='Состояния Обработки')
    products = JSONField(null=True, blank=True)
    json = JSONField(null=True, blank=True)
    received_at = models.DateTimeField(verbose_name='received time from GTK', null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return str(self.request_number)

    @property
    def received_at_in_seconds(self):
        if self.received_at:
            return self.received_at.strftime("%d-%m-%Y %H:%M:%S")
        else:
            return self.received_at

    @property
    def added_at_in_seconds(self):
        if self.added_at:
            return self.added_at.strftime("%d-%m-%Y %H:%M:%S")
        else:
            return self.added_at

    @property
    def updated_at_in_seconds(self):
        if self.updated_at:
            return self.updated_at.strftime("%d-%m-%Y %H:%M:%S")
        else:
            return self.updated_at

    # for application/litst.html
    @property
    def inspector(self):
        return self.owner

    @property
    def request_and_contract_info(self):
        if self.importer_contract_number and self.importer_contract_date:
            return f"Номер заявки: {self.request_number} контракт № {self.importer_contract_number} от {str(self.importer_contract_date)}"
        else:
            return f"Номер заявки: {self.request_number}"

    @property
    def processing_time_in_minutes(self):
        try:
            ikr = self.ikr
            if ikr.approved_at:
                return int((self.ikr.approved_at - self.added_at).total_seconds() / 60)
            else:
                return int((datetime.datetime.now() - self.added_at).total_seconds() / 60)
        except:
            return int((datetime.datetime.now() - self.added_at).total_seconds() / 60)

    @property
    def processing_time(self):
        processing_time_in_hours = int(self.processing_time_in_minutes / 60)
        processing_time_in_days = int(processing_time_in_hours / 24)
        spending_days = processing_time_in_days
        spending_hours = processing_time_in_hours - processing_time_in_days * 24
        return f'{spending_days} дней и {spending_hours} часы'

    class Meta:
        verbose_name = 'Applicant for IKR'
        verbose_name_plural = 'Applicants for IKRs'
        ordering = ['pk']
        db_table = 'ikr_application'
        default_permissions = ()

        permissions = (
            ('list_ikr_application', f'Can list {verbose_name}'),
            ('consider_ikr_application', f'Can consider {verbose_name}')
        )


class IKRApplicationStatusStep(models.Model):
    application = models.ForeignKey(IKRApplication, on_delete=models.CASCADE, related_name='status_steps',
                                    verbose_name='IKR Application')
    status = models.IntegerField(choices=ApplicationStatuses.CHOICES, default=ApplicationStatuses.ONE_ZERO_ZERO,
                                 verbose_name='Status')
    description = models.CharField(max_length=500, verbose_name='Причина', null=True, blank=True)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Отправитель', null=True, blank=True)
    sender_name = models.CharField(max_length=200, null=True, blank=True)
    sender_phone = models.CharField(max_length=50, null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.description

    @property
    def sender_name_ru(self):
        if self.sender:
            return self.sender.name_local
        else:
            return self.sender_name

    @property
    def sender_phone_number(self):
        if self.sender:
            return self.sender.phone
        else:
            return self.sender_phone

    class Meta:
        verbose_name = 'IKR Application Status Step'
        verbose_name_plural = 'IKR Application Status Steps'
        db_table = 'ikr_application_status_step'
        ordering = ['pk']
        default_permissions = ()


class IKR(models.Model):
    application = models.OneToOneField(IKRApplication, on_delete=models.SET_NULL, default=None, null=True, blank=True)
    number = models.CharField(unique=True, max_length=15, verbose_name='ИКР №', null=True, blank=True)
    crpp_number = models.CharField(unique=True, max_length=40, null=True, blank=True)
    language = models.IntegerField(choices=Languages.CHOICES, default=Languages.RUSSIAN,
                                   verbose_name='Язык сертификата')
    given_date = models.DateField(verbose_name='Выдано', null=True, blank=True)
    expire_date = models.DateField(verbose_name='Cроком до', null=True, blank=True)
    request_number = models.CharField(unique=True, max_length=30, verbose_name='Номер заявки')
    request_date = models.DateField(verbose_name='Дата заявления')
    applicant_type = models.IntegerField(choices=CustomerType.CHOICES, verbose_name='Налогоплательщик', null=True,
                                         blank=True)
    applicant_tin = models.CharField(verbose_name='ИНН', max_length=15, null=True, blank=True)
    applicant_name = models.CharField(max_length=150, verbose_name='Наименование заявителя/организации', null=True,
                                      blank=True)
    applicant_representative_name = models.CharField(max_length=150, verbose_name='Ф.И.О. руководителя', null=True,
                                                     blank=True)
    applicant_region = models.ForeignKey(Region, on_delete=models.DO_NOTHING, verbose_name='регион', null=True,
                                         blank=True, related_name='applicants')
    applicant_address = models.CharField(max_length=300, verbose_name='Адрес', null=True, blank=True)
    applicant_phone = models.CharField(max_length=35, verbose_name='Телефон', null=True, blank=True)
    applicant_fax = models.CharField(max_length=35, verbose_name='Факс', null=True, blank=True)
    importer_type = models.IntegerField(choices=CustomerType.CHOICES, verbose_name='Налогоплательщик')
    importer_tin = models.CharField(verbose_name='ИНН', max_length=15, null=True, blank=True)
    importer_name = models.CharField(max_length=150, verbose_name='Наименование импортера/организации')
    importer_representative_name = models.CharField(max_length=150, verbose_name='Ф.И.О. руководителя')
    importer_region = models.ForeignKey(Region, on_delete=models.DO_NOTHING,
                                        verbose_name='регион', null=True, blank=True)
    importer_address = models.CharField(max_length=300, verbose_name='Адрес', null=True, blank=True)
    importer_phone_number = models.CharField(max_length=35, verbose_name='Телефон', null=True, blank=True)
    importer_fax = models.CharField(max_length=35, verbose_name='Факс', null=True, blank=True)
    exporter_organization_name = models.CharField(max_length=150, verbose_name='Наименование экспортера', null=True,
                                                  blank=True)
    exporter_country = models.ForeignKey(Country, on_delete=models.CASCADE, verbose_name='Экспортирующая страна',
                                         related_name='ikrs')
    exporter_address = models.CharField(max_length=300, verbose_name='Адрес и наименование места производства',
                                        null=True, blank=True)
    importer_contract_number = models.CharField(max_length=200, verbose_name='Номер импортного контракта', null=True,
                                                blank=True)
    importer_contract_date = models.DateField(verbose_name='Дата импортного контракта', null=True, blank=True)
    transit_exporter_country = models.ForeignKey(Country, on_delete=models.CASCADE, verbose_name='Транзит (от)',
                                                 related_name='transit_exporter_country_ikr', null=True, blank=True)
    transit_importer_country = models.ForeignKey(Country, on_delete=models.CASCADE, verbose_name='Транзит (до)',
                                                 related_name='transit_importer_country_ikr', null=True, blank=True)
    transport_method = models.IntegerField(choices=TransPortTypes.choices, verbose_name='Метод транспортировки',
                                           null=True, blank=True)
    point = models.ForeignKey(Point, on_delete=models.CASCADE,
                              verbose_name='Наименование пункта назначения (место растаможки груза)')
    entering_point_in_transit = models.ForeignKey(Point, on_delete=models.CASCADE, null=True, blank=True,
                                                  verbose_name='Транзит (от)',
                                                  related_name='entering_point_in_transit_ikr')
    leaving_point_in_transit = models.ForeignKey(Point, on_delete=models.CASCADE, null=True, blank=True,
                                                 verbose_name='Транзит (до)',
                                                 related_name='leaving_point_in_transit_ikr')
    expected_entering_date_in_transit = models.DateField(verbose_name='Ожидаемый срок транзита: (с даты)', null=True,
                                                         blank=True)
    expected_leaving_date_in_transit = models.DateField(verbose_name='Ожидаемый срок транзита: (по дату)', null=True,
                                                        blank=True)
    registered_number = models.CharField(max_length=45, verbose_name='Регистрационный номер сертификата', null=True,
                                         blank=True)
    request_and_contract_info = models.CharField(max_length=4000,
                                                 verbose_name='Основания для выпуска разрешительного документа',
                                                 null=True, blank=True)
    route = models.CharField(max_length=4000, verbose_name='Маршрут транспортировки (пункт погранперехода)', null=True,
                             blank=True)
    expected_date_of_sending_products = models.DateField(verbose_name='Ожидаемый срок отправки материала', null=True,
                                                         blank=True)
    expected_date_of_arrivaling_products = models.DateField(verbose_name='Ожидаемый срок прибытия материала', null=True,
                                                            blank=True)
    used_place_of_products = models.CharField(max_length=4000, verbose_name='Место использования материалов', null=True,
                                              blank=True)
    used_purpose_of_products = models.CharField(max_length=4000, verbose_name='Цель использования материалов',
                                                null=True, blank=True)
    certificate_of_disinfestation_number = models.CharField(max_length=1000, null=True, blank=True)
    undertaken_quarantine = models.CharField(max_length=4055, verbose_name='Содержание процедуры карантирования',
                                             null=True, blank=True)
    extra_requirement = models.CharField(max_length=4055, verbose_name='Содержание дополнительных требований',
                                         null=True, blank=True)
    extra_pests = models.CharField(max_length=4055,
                                   verbose_name='Информация о вредных организмах имеющих карантинное значение для РУз ',
                                   null=True, blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Owner', null=True, blank=True)
    considered_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='considered person',
                                      related_name='ikr_considered_persons', null=True, blank=True)
    signatory = models.CharField(max_length=155, verbose_name='Ф.И.О. выдающего одобрение', null=True, blank=True)
    is_approved = models.BooleanField(verbose_name='Одобрить да или нет', default=False)
    is_transit = models.BooleanField(default=False)
    is_synchronised = models.BooleanField(default=True)  # TODO before migration make True
    is_active = models.BooleanField(verbose_name='IS Active', default=True)
    payment_amount = models.IntegerField(default=settings.ONE_BASIC_ESTIMATE)
    sms_notification = models.OneToOneField(SMSNotification, on_delete=models.SET_NULL, null=True, blank=True,
                                            related_name='ikr')
    approved_at = models.DateTimeField(verbose_name='Утверждено в', null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    all_objects = models.Manager()
    objects = IsApprovedManager()
    unapproved_objects = IsIKRUnapprovedManager()

    @staticmethod
    def send_sms():
        ikrs = IKR.objects.filter(sms_notification__isnull=True)
        messages = []
        correct_sms_notifications = []
        for ikr in ikrs:
            all_digits = re.findall(r'\d+', ikr.importer_phone_number)
            receiver_phone = "".join(all_digits)[-9:]
            text = "Uzdavkarantin inspeksiyasi\n\n" \
                   "Karantin ruxsatnomasi\n" \
                   f"№ {ikr.number}\n" \
                   f"STIR: {ikr.importer_tin}\n" \
                   f"Berilgan sana: {ikr.given_date.strftime('%d.%m.%Y')}\n" \
                   f"Ko'rish: http://efito.uz:30080/check_certificate?type=ikr&number={ikr.number}"
            sms_notification = SMSNotification.objects.create(
                text=text,
                receiver_phone=receiver_phone,
                purpose=SMSNotificationPurposes.IKR
            )
            if len(receiver_phone) == 9:
                sms_notification.status = SMSNotificationStatuses.REQUESTED
                sms_notification.save()
                messages.append({
                    'recipient': f'998{receiver_phone}',
                    'message-id': sms_notification.message_id,
                    'sms': {
                        'originator': SMS_NOTIFICATION_ORIGINATOR,
                        'content': {
                            'text': text
                        }
                    }
                })
                correct_sms_notifications.append(sms_notification)
            else:
                sms_notification.status = SMSNotificationStatuses.WRONG_NUMBER
                sms_notification.save()

            ikr.sms_notification = sms_notification
            ikr.save()

    def __str__(self):
        return f'№{self.number} - {self.request_number}'

    def get_absolute_url(self):
        return reverse('exim:view_ikr', kwargs={'pk': self.id})

    @property
    def latest_shipment(self):
        return self.shipments.latest()

    @property
    def has_remaining_products(self):
        return IKRProduct.objects.filter(ikr=self, remaining_quantity__gt=0).exists()

    @property
    def deadline(self):
        return self.extensions.latest().expire_date if self.extensions.exists() else self.expire_date

    @property
    def is_valid(self):
        return self.deadline >= datetime.date.today()

    class Meta:
        verbose_name = 'ИКР'
        verbose_name_plural = 'ИКР'
        db_table = 'ikr'
        ordering = ['application__added_at']
        default_permissions = ()

        permissions = (
            ('list_republic_ikr', f'Can list republic {verbose_name}'),
            ('view_republic_ikr', f'Can view republic {verbose_name}'),
            ('add_republic_ikr', f'Can add republic {verbose_name}'),
            ('approve_republic_ikr', f'Can approve republic {verbose_name}'),
            ('add_transit_ikr', f'Can add transit {verbose_name}'),
            ('extend_ikr_expire_date', f'Can extend expire date {verbose_name}'),
        )


class IKRProduct(models.Model):
    ikr = models.ForeignKey(IKR, on_delete=models.CASCADE, related_name='products', verbose_name='ИКР')
    name = models.CharField(max_length=500, verbose_name='Наименование товара')
    lab_name = models.CharField(max_length=500, verbose_name='Наименование товара(Lab)', null=True, blank=True)
    hs_code = models.ForeignKey(HSCode, on_delete=models.CASCADE, verbose_name='KOD TN ved')
    quantity = models.FloatField(default=0.0, verbose_name='Количество')
    remaining_quantity = models.FloatField(default=0.0, verbose_name='Оставшееся количество')
    manufactured_country = models.ForeignKey(Country, on_delete=models.CASCADE, null=True, blank=True,
                                             related_name='ikr_products')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, verbose_name='Единица')
    is_netto = models.BooleanField(verbose_name='IS Netto', default=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.pk:
            self.remaining_quantity = self.quantity
        super(IKRProduct, self).save(*args, **kwargs)

    @property
    def ikr_number(self):
        return self.ikr.number

    class Meta:
        verbose_name = 'ИКР продукт'
        verbose_name_plural = 'ИКР продукты'
        db_table = 'ikr_product'
        ordering = ['-pk']
        default_permissions = ()


class IKRRenewalApplication(models.Model):
    request_number = models.CharField(max_length=30)
    request_date = models.DateField(verbose_name='Request Date')
    ikr = models.ForeignKey(IKR, on_delete=models.CASCADE, verbose_name='IKR')
    extension_date = models.DateField(verbose_name='Дата истечения срока действия сертификата (на продление)')
    applicant_tin = models.CharField(max_length=15)
    importer_tin = models.CharField(max_length=15)
    json = JSONField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Инспектор', null=True, blank=True)
    status = models.IntegerField(choices=ApplicationStatuses.CHOICES, default=ApplicationStatuses.ONE_ZERO_ZERO,
                                 verbose_name='Состояния Обработки')
    received_at = models.DateTimeField(verbose_name='received time from GTK', null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return str(self.request_number) + '(' + str(self.ikr.number) + ')'

    @property
    def importer_name(self):
        return self.ikr.importer_name

    @property
    def importer_representative_name(self):
        return self.ikr.importer_representative_name

    @property
    def importer_phone_number(self):
        return self.ikr.importer_phone_number

    @property
    def received_at_in_seconds(self):
        if self.received_at:
            return self.received_at.strftime("%d-%m-%Y %H:%M:%S")
        else:
            return self.received_at

    @property
    def added_at_in_seconds(self):
        if self.added_at:
            return self.added_at.strftime("%d-%m-%Y %H:%M:%S")
        else:
            return self.added_at

    @property
    def updated_at_in_seconds(self):
        if self.updated_at:
            return self.updated_at.strftime("%d-%m-%Y %H:%M:%S")
        else:
            return self.updated_at

    @property
    def processing_time_in_minutes(self):
        return int((self.updated_at - self.added_at).total_seconds() / 60)

    @property
    def processing_time(self):
        processing_time_in_hours = int(self.processing_time_in_minutes / 60)
        processing_time_in_days = int(processing_time_in_hours / 24)
        spending_days = processing_time_in_days
        spending_hours = processing_time_in_hours - processing_time_in_days * 24
        return f'{spending_days} дней и {spending_hours} часы'

    class Meta:
        verbose_name = 'Applicant for IKR Renewal'
        verbose_name_plural = 'Applicants for IKR Renewals'
        ordering = ['-pk']
        db_table = 'ikr_renewal_applicant'

        permissions = (
            ('list_ikr_renewal_application', f'Can list {verbose_name}'),
            ('consider_ikr_renewal_application', f'Can consider {verbose_name}')
        )


class IKRRenewalApplicationStatusStep(models.Model):
    application = models.ForeignKey(IKRRenewalApplication, on_delete=models.CASCADE, related_name='status_steps',
                                    verbose_name='IKR Renewal Application')
    status = models.IntegerField(choices=ApplicationStatuses.CHOICES, default=ApplicationStatuses.ONE_ZERO_ZERO,
                                 verbose_name='Status')
    description = models.CharField(max_length=500, verbose_name='Причина', null=True, blank=True)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Отправитель', null=True, blank=True)
    sender_name = models.CharField(max_length=200, null=True, blank=True)
    sender_phone = models.CharField(max_length=50, null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.description

    @property
    def sender_name_ru(self):
        if self.sender:
            return self.sender.name_ru
        else:
            return self.sender_name

    @property
    def sender_phone_number(self):
        if self.sender:
            return self.sender.phone
        else:
            return self.sender_phone

    class Meta:
        verbose_name = 'IKR Renewal Application Status Step'
        verbose_name_plural = 'IKR Renewal Application Status Steps'
        db_table = 'ikr_renewal_application_status_step'
        ordering = ['pk']
        default_permissions = ()


class IKRExtension(models.Model):
    ikr = models.ForeignKey(IKR, on_delete=models.CASCADE, related_name='extensions')
    request_number = models.CharField(max_length=30, null=True, blank=True)
    expire_date = models.DateField(verbose_name='Продленный до')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Owner', null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.request_number

    class Meta:
        db_table = 'ikr_extension'
        get_latest_by = 'expire_date'
        default_permissions = ()


class AKDApplication(models.Model):
    request_number = models.CharField(max_length=30)
    transport_number = models.CharField(max_length=1000)
    importer_tin = models.CharField(max_length=15)
    ikr = models.ForeignKey(IKR, on_delete=models.CASCADE, verbose_name='IKR')
    region = models.ForeignKey(Region, on_delete=models.CASCADE, verbose_name='Region')
    json = JSONField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    inspector = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Инспектор', null=True, blank=True)
    status = models.IntegerField(choices=ApplicationStatuses.CHOICES, default=ApplicationStatuses.ONE_ZERO_ZERO,
                                 verbose_name='Состояния Обработки')
    received_at = models.DateTimeField(verbose_name='received time from GTK', null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return str(self.transport_number) + '(' + str(self.ikr.number) + ')'

    @property
    def received_at_in_seconds(self):
        if self.received_at:
            return self.received_at.strftime("%d-%m-%Y %H:%M:%S")
        else:
            return self.received_at

    @property
    def added_at_in_seconds(self):
        if self.added_at:
            return self.added_at.strftime("%d-%m-%Y %H:%M:%S")
        else:
            return self.added_at

    @property
    def updated_at_in_seconds(self):
        if self.updated_at:
            return self.updated_at.strftime("%d-%m-%Y %H:%M:%S")
        else:
            return self.updated_at

    @property
    def processing_time_in_minutes(self):
        try:
            akd = self.ikr_shipment.tbotd.akd
            if akd.is_synchronised:
                return int((akd.updated_at - self.added_at).total_seconds() / 60)
            else:
                return int((datetime.datetime.now() - self.added_at).total_seconds() / 60)
        except:
            return int((datetime.datetime.now() - self.added_at).total_seconds() / 60)

    @property
    def processing_time(self):
        processing_time_in_hours = int(self.processing_time_in_minutes / 60)
        processing_time_in_days = int(processing_time_in_hours / 24)
        spending_days = processing_time_in_days
        spending_hours = processing_time_in_hours - processing_time_in_days * 24
        return f'{spending_days} дней и {spending_hours} часы'

    class Meta:
        verbose_name = 'Applicant for AKD'
        verbose_name_plural = 'Applicants for AKDs'
        ordering = ['-pk']
        db_table = 'akd_applicant'


class AKDApplicationStatusStep(models.Model):
    application = models.ForeignKey(AKDApplication, on_delete=models.CASCADE, related_name='status_steps',
                                    verbose_name='AKD Application')
    status = models.IntegerField(choices=ApplicationStatuses.CHOICES, default=ApplicationStatuses.ONE_ZERO_ZERO,
                                 verbose_name='Status')
    description = models.CharField(max_length=500, verbose_name='Причина', null=True, blank=True)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Отправитель', null=True, blank=True)
    sender_name = models.CharField(max_length=200, null=True, blank=True)
    sender_phone = models.CharField(max_length=50, null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.description

    @property
    def sender_name_ru(self):
        if self.sender:
            return self.sender.name_ru
        else:
            return self.sender_name

    @property
    def sender_phone_number(self):
        if self.sender:
            return self.sender.phone
        else:
            return self.sender_phone

    class Meta:
        verbose_name = 'AKD Application Status Step'
        verbose_name_plural = 'AKD Application Status Steps'
        db_table = 'akd_application_status_step'
        ordering = ['pk']
        default_permissions = ()


class IKRShipment(models.Model):
    ikr = models.ForeignKey(IKR, on_delete=models.CASCADE, related_name='shipments', verbose_name='ИКР')
    akd_application = models.OneToOneField(AKDApplication, on_delete=models.SET_NULL, default=None, null=True,
                                           blank=True, related_name='ikr_shipment')
    number = models.CharField(max_length=20, verbose_name='Номер отгрузки, формат: ГГНомер доставки', unique=True,
                              null=True)
    info = models.CharField(max_length=90, verbose_name='Информация')
    fito_number = models.CharField(max_length=128, verbose_name='ФИТО №', null=True, blank=True)
    fito_given_date = models.CharField(max_length=256, verbose_name='ФИТО Giv Дата', null=True, blank=True)
    fito_expire_date = models.DateField(verbose_name='ФИТО Exp Дата', null=True, blank=True)
    representative_name = models.CharField(max_length=150, verbose_name='Имя представителя', null=True, blank=True)
    representative_passport_number = models.CharField(max_length=10, verbose_name='Номер паспорта представителя',
                                                      null=True, blank=True)
    representative_phone = models.CharField(max_length=20, verbose_name='Телефон представителя', null=True, blank=True)
    is_confirmed = models.BooleanField(default=True)
    confirmed_date = models.DateField(verbose_name='confirmed Дата', null=True)
    status = models.IntegerField(choices=IKRShipmentStatuses.CHOICES, default=IKRShipmentStatuses.COMING,
                                 verbose_name='Положение дел.')
    registerer_point = models.ForeignKey(Point, on_delete=models.CASCADE, verbose_name='Точка регистрации')
    sent_at = models.DateTimeField(verbose_name='Sent time from UKCHM', null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    inspector = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Инспектор')
    sms_notification = models.OneToOneField(SMSNotification, on_delete=models.SET_NULL, null=True, blank=True,
                                            related_name='ikr_shipment')
    unique_registered_number_in_gtk = models.CharField(max_length=50, verbose_name='Ягона қайд варақаси рақами', null=True, blank=True)
    unique_registered_file_in_gtk = models.FileField(null=True, blank=True, upload_to='unique_registered_files_in_gtk/')

    objects = IKRShipmentManager()

    def __str__(self):
        return self.info

    @property
    def ikr_number(self):
        return self.ikr.number

    @property
    def is_notified(self):
        return self.sms_notification is not None

    @property
    def akds(self):
        return AKD.objects.filter(tbotd__ikr_shipment__ikr=self)

    @property
    def akd(self):
        return self.tbotd.akd

    @property
    def deadline(self):
        return self.added_at + datetime.timedelta(seconds=TIME_FOR_SHIPMENT)

    def has_add_tbotd_permission(self, user=None):
        ikr = self.ikr
        return (not user and hasattr(self, 'tbotd')) or (user.has_perm('exim.add_point_tbotd')
                                                         and (ikr.point == user.point or ikr.point.code == '00000')
                                                         and not hasattr(self, 'tbotd'))

    def transit_can_be_added(self, user=None):
        ikr = self.ikr
        return (not user and hasattr(self, 'transit')) or (user.has_perm('exim.add_point_transit')
                                                           and (ikr.leaving_point_in_transit == user.point)
                                                           and not hasattr(self, 'transit'))

    def has_change_permission(self, user=None):
        in_suitable_status = self.status in IKRShipmentStatuses.editable_shipment_statuses
        # current = datetime.datetime.now()
        # shipment_change_deadline = datetime.timedelta(seconds=TIME_FOR_CHANGE_IKRSHIPMENT)
        # added_at = self.added_at
        return (not user and in_suitable_status) or (user.has_perm('exim.change_inspector_ikrshipment') and
                                                     in_suitable_status and
                                                     (self.inspector == user or self.ikr.point == user.point or
                                                      self.ikr.point.code == '00000'))

    def has_delete_permission(self, user=None):
        in_suitable_status = self.status in IKRShipmentStatuses.editable_shipment_statuses
        return (not user and in_suitable_status) or \
               (user.has_perm('exim.delete_inspector_ikrshipment') and in_suitable_status and user == self.inspector)

    @staticmethod
    def send_sms():
        ikr_shipments = IKRShipment.objects.filter(sms_notification__isnull=True)
        messages = []
        correct_sms_notifications = []
        for ikr_shipment in ikr_shipments:
            ikr = ikr_shipment.ikr
            all_digits = re.findall(r'\d+', ikr.importer_phone_number)
            receiver_phone = "".join(all_digits)[-9:]
            text = f"UZDAVKARANTIN\n" \
                   f"STIR: {ikr.importer_tin}\n" \
                   f"KR: {ikr.number}\n" \
                   f"Transport: {TransPortTypes.local_names.get(ikr.transport_method)}({ikr_shipment.info})\n" \
                   f"UKChM/TIF: {ikr_shipment.registerer_point.name_local}\n" \
                   f"Qayd etilgan vaqt: {ikr_shipment.added_at.strftime('%d.%m.%Y %H:%M')}"
            sms_notification = SMSNotification.objects.create(
                text=text,
                receiver_phone=receiver_phone,
                purpose=SMSNotificationPurposes.IKR_SHIPMENT
            )
            if len(receiver_phone) == 9:
                sms_notification.status = SMSNotificationStatuses.REQUESTED
                sms_notification.save()
                messages.append({
                    'recipient': f'998{receiver_phone}',
                    'message-id': sms_notification.message_id,
                    'sms': {
                        'originator': SMS_NOTIFICATION_ORIGINATOR,
                        'content': {
                            'text': text
                        }
                    }
                })
                correct_sms_notifications.append(sms_notification)
            else:
                sms_notification.status = SMSNotificationStatuses.WRONG_NUMBER
                sms_notification.save()

            ikr_shipment.sms_notification = sms_notification
            ikr_shipment.save()

        if messages:
            request_body = {
                'messages': messages
            }
            with requests.Session() as s:
                try:
                    proxies = {'http': 'http://192.168.145.2:3128'}
                    response = s.post(auth=HTTPBasicAuth('karantinuz', 'AB6ciQvf'),
                                      url=f'{SMS_NOTIFICATION_API_BASE_URL}send',
                                      json=request_body,
                                      proxies=proxies)
                except Exception:
                    for correct_sms_notification in correct_sms_notifications:
                        correct_sms_notification.delete()
                    return

            if response.status_code != 200:
                for correct_sms_notification in correct_sms_notifications:
                    correct_sms_notification.delete()

    @property
    def is_on_time(self):
        return self.deadline > timezone.now()

    def save(self, *args, **kwargs):
        if not self.pk:
            super(IKRShipment, self).save()
            self.number = int(datetime.datetime.now().strftime('%y')) * 100000000000000 + self.pk
            self.save()
        else:
            super(IKRShipment, self).save()

    class Meta:
        verbose_name = 'Отгрузка ИКР'
        verbose_name_plural = 'Отгрузки ИКР'
        db_table = 'ikr_shipment'
        get_latest_by = 'added_at'
        ordering = ('-added_at',)
        default_permissions = ()

        permissions = (
            # republic
            ('list_republic_ikrshipment', f'Can list republic {verbose_name}'),

            # region
            # ('list_region_ikrshipment', f'Can list region {verbose_name}'),

            # point
            ('list_point_ikrshipment', f'Can list point {verbose_name}'),
            ('add_point_ikrshipment', f'Can add point {verbose_name}'),

            # inspector
            ('list_own_ikrshipment', f'Can list own {verbose_name}'),
            ('delete_inspector_ikrshipment', f'Can delete inspector {verbose_name}'),
            ('change_inspector_ikrshipment', f'Can change inspector {verbose_name}')
        )


class IKRShipmentProduct(models.Model):
    ikr_shipment = models.ForeignKey(IKRShipment, on_delete=models.CASCADE,
                                     related_name='products', verbose_name='Отгрузка')
    ikr_product = models.ForeignKey(IKRProduct, on_delete=models.CASCADE,
                                    related_name='shipment_products', verbose_name='Продукт')
    quantity = models.FloatField(default=0, verbose_name='Количество')
    is_damaged = models.BooleanField(default=False,
                                     verbose_name='Поврежден?')
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    order_number = models.CharField(max_length=5, null=True, blank=True, verbose_name='Номер серии продукции')
    ikr_product_order_number = models.CharField(max_length=5, null=True, blank=True, verbose_name='Номер товара по КР')

    objects = IKRShipmentProductManager()

    def __str__(self):
        return str(self.quantity) + self.ikr_product.name

    @property
    def name(self):
        return self.ikr_product.name

    @property
    def hs_code(self):
        return self.ikr_product.hs_code

    @property
    def unit_name(self):
        return self.ikr_product.unit.name_ru

    def __str__(self):
        return self.ikr_product.name

    class Meta:
        verbose_name = 'Отгрузка ИКР продукт'
        verbose_name_plural = 'Отгрузки ИКР продукты'
        db_table = 'ikr_shipment_product'
        default_permissions = ()


class TBOTD(models.Model):
    ikr_shipment = models.OneToOneField(IKRShipment, on_delete=models.CASCADE, related_name='tbotd',
                                        verbose_name='Отгрузка ИКР')
    inspector = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Инспектор')
    number = models.CharField(max_length=20, unique=True, null=True, verbose_name='№')
    given_date = models.DateField(auto_now_add=True, verbose_name='Дано в')
    lab_shortcut = models.ForeignKey('lab.ImportShortcut', on_delete=models.SET_NULL, default=None,
                                     null=True, blank=True, related_name='tbotds')
    must_fumigated = models.BooleanField(default=False, verbose_name='Fumigatsiya qilinsin!')
    extra_info = models.CharField(max_length=200, null=True, verbose_name='Транспорт воситаси очилган манзили ва омбор номи')
    beginning_of_action = models.DateTimeField(null=True, blank=True, verbose_name='Транспорт воситасининг очилиш вақти')
    ending_of_action = models.DateTimeField(null=True, blank=True, verbose_name='Транспорт воситасининг кўриги тугаш вақти')
    agro_monitored = models.BooleanField(default=False)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    @property
    def products(self):
        return self.ikr_shipment.products

    @property
    def ikr(self):
        return self.ikr_shipment.ikr

    @property
    def spent_time(self):
        spent_time = {'hours': 'киритилмаган', 'minutes': 'киритилмаган'}
        if self.ending_of_action and self.beginning_of_action:
            spent_time_in_minutes = int((self.ending_of_action - self.beginning_of_action).total_seconds() / 60)
            spent_time['minutes'] = spent_time_in_minutes % 60
            spent_time['hours'] = int((spent_time_in_minutes - spent_time['minutes']) / 60)
        return spent_time

    def has_add_akd_permission(self, user=None):
        ikr_shipment = self.ikr_shipment
        is_suitable_status = ikr_shipment.status in IKRShipmentStatuses.allowed_statuses_for_akd.keys()
        has_active_products = ikr_shipment.products.filter(is_damaged=False).exists()
        return (user.has_perm('exim.add_point_akd')
                and is_suitable_status
                and (ikr_shipment.ikr.point == user.point)
                and has_active_products
                )

    def __str__(self):
        return str(self.number)

    def has_delete_permission(self, user=None):
        is_suitable_status = self.ikr_shipment.status in IKRShipmentStatuses.editable_shipment_statuses
        return (not user and is_suitable_status) or \
               (user.has_perm('exim.delete_inspector_tbotd') and is_suitable_status and user == self.inspector)

    def has_view_permission(self, user=None):
        can_view = False
        if user.has_perm('exim.view_republic_tbotd'):
            can_view = True
        elif user.has_perm('exim.view_region_tbotd') and self.ikr_shipment.ikr.point.region == user.point.region:
            can_view = True
        elif user.has_perm('exim.view_point_tbotd') and self.ikr_shipment.ikr.point.region == user.point.region:
            can_view = True

        return can_view

    @property
    def balance(self):
        # start checking balance
        region = self.ikr.point.region
        tin = self.ikr.importer_tin
        first_day_of_month = '2022-01-01'
        service_type = InvoiceServices.TBOTD

        balance = Balance.objects.filter(organization__tin=tin, month=first_day_of_month, region=region,
                                         service_type=service_type).first()
        invoices_payments = InvoicePayment.objects.confirmed().filter(invoice__applicant_tin=tin,
                                                                      invoice__service_type=service_type,
                                                                      invoice__region=region,
                                                                      payment_date__gte=first_day_of_month)
        contract_payments = ContractPayment.objects.filter(organization__tin=tin,
                                                           region=region,
                                                           service_type=service_type,
                                                           payment_date__gte=first_day_of_month)
        refunds = Refund.objects.filter(organization__tin=tin,
                                        region=region,
                                        service_type=service_type,
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

        akds = AKD.objects.filter(tbotd__ikr_shipment__ikr__point__region=region,
                                  tbotd__ikr_shipment__ikr__importer_tin=tin,
                                  given_date__gte=first_day_of_month)

        if akds:
            service_amount = akds.aggregate(Sum('payment_amount'))['payment_amount__sum']

        current_balance = current_balance - service_amount
        # end checking balance
        return current_balance - settings.ONE_BASIC_ESTIMATE

    class Meta:
        verbose_name = 'TBOTD'
        verbose_name_plural = 'TBOTD'
        db_table = 'tbotd'
        ordering = ('-id',)
        default_permissions = ()

        permissions = (
            # republic
            ('list_republic_tbotd', f'Can list republic {verbose_name}'),
            ('view_republic_tbotd', f'Can view republic {verbose_name}'),

            # region
            ('list_region_tbotd', f'Can list region {verbose_name}'),
            ('view_region_tbotd', f'Can view region {verbose_name}'),

            # point
            ('add_point_tbotd', f'Can add point {verbose_name}'),
            ('list_point_tbotd', f'Can list point {verbose_name}'),
            ('view_point_tbotd', f'Can view point {verbose_name}'),

            # inspector
            ('delete_inspector_tbotd', f'Can delete inspector {verbose_name}')
        )


class TBOTDExtraInfo(models.Model):
    tbotd = models.OneToOneField(TBOTD, on_delete=models.PROTECT, null=True, blank=True, related_name='tbotd_extra_info')
    quarantine_control_process = models.FileField(null=True, blank=True, upload_to='exim/tbotd/extra_info/')
    importer_info = models.FileField(null=True, blank=True, upload_to='exim/tbotd/extra_info/')
    certificate_of_disinfestation = models.ForeignKey(CertificateOfDisinfestation, on_delete=models.CASCADE, null=True, blank=True)
    inspector = models.ForeignKey(User, on_delete=models.CASCADE)
    is_completed = models.BooleanField(default=False)
    added_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def can_edit_as_inspector(self, user=None):
        if self.tbotd.ikr_shipment.ikr.point == user.point and not self.is_completed:
            return True
        else:
            return False

    def can_complete_as_inspector(self, user=None):
        if self.tbotd.ikr_shipment.ikr.point == user.point and self.tbotd.ikr_shipment.status == IKRShipmentStatuses.AGRO_MONITORING and not self.is_completed:
            return True
        else:
            return False

    @property
    def is_on_time(self):
        return self.added_at + datetime.timedelta(seconds=432000) > timezone.now()

    # def save(self, *args, **kwargs):
    #     if not self.pk:
    #         print('sssssssqaaaaaaa')
    #         if self.quarantine_control_process:
    #             print('sssssssss')
    #             extension = self.quarantine_control_process.name.split('.')[-1]
    #             # print('extension')
    #             # print(extension)
    #             # if extension in ['pdf', 'rar', 'zip', 'doc', 'docx']:
    #             self.quarantine_control_process.name = os.path.join('exim/tbotd/extra_info', f'{uuid.uuid4()}.{extension}')
    #             super(TBOTDExtraInfo, self).save()
    #             # else:
    #             #     raise Exception("Invalid format or Authentication token")
    #     else:
    #         super(TBOTDExtraInfo, self).save()

    class Meta:
        db_table = 'tbotd_extra_info'
        default_permissions = ()

        permissions = (
            ('can_approve_tbotd_extra_info', 'Can approve tbotd extra info'),
        )


class TBOTDRejectionInfo(models.Model):
    tbotd = models.OneToOneField(to=TBOTD, on_delete=models.CASCADE, related_name='rejection_info')
    proof_file = models.FileField()
    inspector = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Инспектор')
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')

    def save(self, *args, **kwargs):
        if not self.pk:
            extension = self.proof_file.name.split('.')[-1]
            self.proof_file.name = os.path.join('exim/tbotd/rejections', f'{uuid.uuid4()}.{extension}')
            super(TBOTDRejectionInfo, self).save()
        else:
            super(TBOTDRejectionInfo, self).save()

    class Meta:
        db_table = 'rejected_tbotd_info'
        default_permissions = ()


class AKD(models.Model):
    tbotd = models.OneToOneField(TBOTD, on_delete=models.CASCADE, related_name='akd', verbose_name='TBOTD')
    inspector = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Инспектор')
    number = models.CharField(max_length=15, unique=True, null=True, verbose_name='№')
    conclusion = models.TextField(verbose_name='Вывод')
    given_date = models.DateField(auto_now_add=True, verbose_name='Дано в')
    representative_full_name = models.CharField(max_length=150, null=True, blank=True,
                                                verbose_name='Представитель организации')
    fumigation_number = models.CharField(max_length=64, verbose_name='Fumigation №', null=True, blank=True)
    fumigation_given_date = models.DateField(verbose_name='Fumigation Given Дата', null=True, blank=True)
    importer_tin = models.CharField(verbose_name='ИНН заявителя', max_length=15, null=True)
    payment_amount = models.IntegerField(default=settings.ONE_BASIC_ESTIMATE)
    is_synchronised = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sms_notification = models.OneToOneField(SMSNotification, on_delete=models.SET_NULL, null=True, blank=True,
                                            related_name='akd')
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    all_objects = models.Manager()
    objects = IsActiveManager()

    @property
    def ikr_shipment(self):
        return self.tbotd.ikr_shipment

    @property
    def application(self):
        return self.ikr_shipment.akd_application

    @property
    def ikr(self):
        return self.ikr_shipment.ikr

    @property
    def products(self):
        return self.ikr_shipment.products.filter(is_damaged=False)

    @property
    def representative_name(self):
        if self.representative_full_name:
            return str(self.representative_full_name)
        else:
            return self.ikr_shipment.representative_name

    def has_delete_permission(self, user=None):
        return (not user and self.is_synchronised) or \
               (user.has_perm('exim.delete_inspector_akd') and self.is_synchronised)

    def sent_to_gtk(self, request, tbotd=None, ikr_shipment=None, akd_application=None, ikr=None, redirect_url=None):
        locale.setlocale(locale.LC_ALL, 'ru_RU')  # to show months in russian messages
        number = self.number
        requests.get('http://127.0.0.1:' + str(os.getenv('RUNNING_PORT')) + str(reverse('exim:download_akd', kwargs={'number': number})))

        file_name = 'akd_' + str(number)
        fs = FileSystemStorage()
        akd_file = f'blanks/{file_name}.pdf'  # look up file from media automatically
        if not fs.exists(akd_file):
            requests.get('http://127.0.0.1:' + str(os.getenv('RUNNING_PORT')) + str(
                reverse('exim:download_akd', kwargs={'number': number})))

        try:
            with open("media/blanks/{}.pdf".format(file_name), 'rb') as binary_file:
                binary_file_data = binary_file.read()
                base64_encoded_data = base64.b64encode(binary_file_data)
                base64_message = base64_encoded_data.decode('utf-8')
            os.remove(f'media/blanks/{file_name}.pdf')  # remove new_invoice after downloading
        except:
            requests.get('http://127.0.0.1:' + str(os.getenv('RUNNING_PORT')) + str(
                reverse('exim:download_akd', kwargs={'number': self.number})))
            messages.error(request, '3 сониядан кейин қайта уриниб кўринг.')
            return HttpResponseRedirect(redirect_url)

        tbotd = tbotd if tbotd else self.tbotd
        ikr_shipment = ikr_shipment if ikr_shipment else tbotd.ikr_shipment
        akd_application = akd_application if akd_application else ikr_shipment.akd_application
        ikr = ikr if ikr else self.ikr
        user = self.inspector

        if akd_application:
            if self.ikr.importer_type == 1:
                importer_type_code = '001'
                importer_type_name = CustomerType.dictionary[1]
            else:
                importer_type_code = '002'
                importer_type_name = CustomerType.dictionary[2]

            products_in_json = [{"CRPP_NO": str(self.number),  # must_be_unique
                                 "CMDT_SRNO": product.order_number if product.order_number else str(index + 1),
                                 "RQST_NO": akd_application.request_number,  # must_be_unique
                                 "HS_CD": product.ikr_product.hs_code.code,
                                 "CMDT_NM": product.ikr_product.name,
                                 "CMDT_QTY": "",
                                 "CMDT_QTY_UT_CD": "",
                                 "CMDT_QTY_UT_NM": "",
                                 "CMDT_TTWG": format(product.quantity, '.3f'),
                                 "CMDT_TTWG_UT_CD": str(product.ikr_product.unit.code),
                                 "CMDT_TTWG_UT_NM": product.ikr_product.unit.name_ru,
                                 "TSCR_NO_NM": self.ikr_shipment.info,
                                 "TSCR_NO_NM_NEW": self.ikr_shipment.info,
                                 "FRST_REGST_ID": akd_application.json['FRST_REGST_ID'],
                                 "FRST_RGSR_DTL_DTTM": akd_application.json['FRST_RGSR_DTL_DTTM'],
                                 "LAST_CHPR_ID": str(user.tin),
                                 "LAST_CHNG_DTL_DTTM": self.added_at.strftime("%Y-%m-%d %H:%M:%S"),
                                 "TSCR_NO_NM": str(10000000 + product.ikr_product.pk),
                                 "IMP_QUAP_CMDT_SRNO": product.ikr_product_order_number if product.ikr_product_order_number else str(
                                     index + 1)
                                 } for index, product in enumerate(self.products)]

            status_json_data = {
                "AKDSert_Information": {"Information_Date": self.added_at.strftime("%Y-%m-%d %H:%M:%S"),
                                        "AKD_Sert": {
                                            "CRPP_NO": str(self.number),
                                            "RQST_NO": akd_application.request_number,
                                            "DOC_NO": "ED-POT-RES-024",
                                            "DOC_NM": "АКД",
                                            "DOC_FNCT_CD": "106",
                                            "CRPP_ISS_BASE_NM": akd_application.json['CRPP_ISS_BASE_NM'],
                                            "CRPP_ISS_BASE_NM_NEW": ikr_shipment.info,
                                            "CRPP_LNGA_TPCD": "RU",
                                            "CRPP_LNGA_TP_NM": "Русский язык",
                                            "RQST_DT": akd_application.json['RQST_DT'],
                                            "CRPP_PBLS_ITT_CD": ikr.point.region.gtk_code,
                                            "CRPP_PBLS_ITT_NM": ikr.point.region.name_ru + 'территориальная инспекция  по карантину растений',
                                            "CRPP_PBLS_ITT_REGN_TPCD": ikr.point.region.code,
                                            "CRPP_PBLS_ITT_REGN_TP_NM": ikr.point.region.name_ru,
                                            "CRPP_PBLS_ITT_ADDR": "",
                                            "FMD_NO": str(self.number),
                                            "CRPP_VALT_PRID_STRT_DT": self.given_date.strftime("%Y-%m-%d"),
                                            "CRPP_VALT_PRID_XPIR_DT": '',
                                            "CRPP_PBLS_DT": self.given_date.strftime("%Y-%m-%d"),
                                            "IMEX_TPCD": "001",
                                            "IMEX_TP_NM": "Импорт",
                                            "APLC_TPCD": akd_application.json['APLC_TPCD'],
                                            "APLC_TP_NM": akd_application.json['APLC_TP_NM'],
                                            "APLC_TXPR_UNIQ_NO": str(ikr.importer_tin),
                                            "APLC_NM": ikr.importer_name,
                                            "APLC_RPPN_NM": ikr.importer_representative_name,
                                            "APLC_REGN_TPCD": ikr.importer_region.code,
                                            "APLC_REGN_TP_NM": ikr.importer_address,
                                            "APLC_ADDR": ikr.importer_phone_number,
                                            "APLC_TELNO": akd_application.json['APLC_TELNO'],
                                            "APLC_FAX_NO": akd_application.json['APLC_FAX_NO'],
                                            "IMPPN_TPCD": importer_type_code,
                                            "IMPPN_TP_NM": importer_type_name,
                                            "IMPPN_TXPR_UNIQ_NO": str(ikr.importer_tin),
                                            "IMPPN_NM": ikr.importer_name,
                                            "IMPPN_RPPN_NM": ikr.importer_representative_name,
                                            "IMPPN_REGN_TPCD": ikr.importer_region.code,
                                            "IMPPN_REGN_TP_NM": ikr.importer_region.name_ru,
                                            "IMPPN_ADDR": ikr.importer_address,
                                            "IMPPN_TELNO": ikr.importer_phone_number,
                                            "IMPPN_FAX_NO": "",
                                            "EXPPN_NM": ikr.exporter_organization_name,
                                            "EXCY_CD": ikr.exporter_country.code,
                                            "EXCY_NM": ikr.exporter_country.name_ru,
                                            "EXPPN_ADDR": ikr.exporter_address,
                                            "TRNP_METH_CD": "0" + str(ikr.transport_method),
                                            "TRNP_METH_NM": TransPortTypes.gtk_dictionary[ikr.transport_method],
                                            "TRNP_METH_GCNT": "1",
                                            "ARLC_REGN_TPCD": ikr.point.region.code,
                                            "ARLC_REGN_TP_NM": ikr.point.name_ru,
                                            "ARLC_CSTM_CD": ikr.point.code,
                                            "ARLC_CSTM_NM": ikr.point.region.name_ru,
                                            "INSC_DT": ikr_shipment.added_at.strftime("%Y-%m-%d"),
                                            "ISPR_ID": str(self.inspector.tin),
                                            "ISPR_NM": self.inspector.name_ru,
                                            "QUAN_RSLT_CN": self.conclusion,
                                            "IMP_QUAN_WRPR_NO": ikr.number,
                                            "APRE_YN": "Y",
                                            "CERTIFICATE_FILE_EXT": "pdf",
                                            "CERTIFICATE_FILE": base64_message,
                                            "PRICHINA": "Одобрение",
                                            "USER_FULL_NAME": user.name_ru,
                                            "USER_PHONE": user.phone,
                                            "USER_ACTION_DATE": self.added_at.strftime("%Y-%m-%d %H:%M:%S"),
                                            "USER_POSITION": user.point.region.name_ru + "карантин",
                                            "USER_INN": str(user.tin),
                                            "ORGAN_ID": user.point.region.gtk_code,
                                            "ORGAN_NAME": user.point.region.name_ru + "карантин",
                                            "ORGAN_PHONE": user.point.region.phone,
                                            "FRST_REGST_ID": akd_application.json['FRST_REGST_ID'],
                                            "FRST_RGSR_DTL_DTTM": akd_application.json['FRST_RGSR_DTL_DTTM'],
                                            "LAST_CHPR_ID": str(user.tin),
                                            "LAST_CHNG_DTL_DTTM": self.added_at.strftime("%Y-%m-%d %H:%M:%S"),
                                            "Tovar": products_in_json
                                        }
                                        }
            }
            integration = Integration.objects.filter(organization_code='GTK',
                                                     data_type=IntegratedDataType.AKD).last()
            IntegrationData.objects.create(
                integration=integration,
                data=status_json_data
            )

            AKDApplicationStatusStep.objects.create(
                application=akd_application,
                status=ApplicationStatuses.ONE_ZERO_SIX,
                description='Одобрение',
                sender=user,
            )
            akd_application.inspector = user
            akd_application.status = ApplicationStatuses.ONE_ZERO_SIX
            akd_application.save()

            self.is_synchronised = True
            self.save()

    # @property
    # def protocol_number(self):
    #     return self.tbotd.lab_shortcut.protocol.number

    def __str__(self):
        return str(self.number)

    @staticmethod
    def send_sms():
        akds = AKD.objects.filter(sms_notification__isnull=True)
        messages = []
        correct_sms_notifications = []
        for akd in akds:
            all_digits = re.findall(r'\d+', akd.ikr.importer_phone_number)
            receiver_phone = "".join(all_digits)[-9:]
            importer_name = akd.ikr.importer_name
            importer_name = (importer_name if not len(importer_name) >= 15 else
                             importer_name[0:15] + '...') if importer_name else ''
            tin = akd.ikr.importer_tin
            tin = f"STIR: {tin}\n" if tin else f"Tashkilot nomi: {importer_name}\n"
            try:
                given_date = f"Berilgan sanasi: {datetime.datetime.strptime(akd.given_date, '%Y-%m-%d').strftime('%d.%m.%Y')}"
            except:
                given_date = ''
            text = "Uzdavkarantin inspeksiyasi\n" \
                   "Karantin ko'rigi dalolatnomasi\n" \
                   f"№ {akd.number}\n" \
                   f"{tin}" \
                   f"{given_date}" \
                   f"Ko\'rish: http://efito.uz/check_certificate?type=akd&number={akd.number}"
            sms_notification = SMSNotification.objects.create(
                text=text,
                receiver_phone=receiver_phone,
                purpose=SMSNotificationPurposes.AKD
            )
            if len(receiver_phone) == 9:
                sms_notification.status = SMSNotificationStatuses.REQUESTED
                sms_notification.save()
                messages.append({
                    'recipient': f'998{receiver_phone}',
                    'message-id': sms_notification.message_id,
                    'sms': {
                        'originator': SMS_NOTIFICATION_ORIGINATOR,
                        'content': {
                            'text': text
                        }
                    }
                })
                correct_sms_notifications.append(sms_notification)
            else:
                sms_notification.status = SMSNotificationStatuses.WRONG_NUMBER
                sms_notification.save()

            akd.sms_notification = sms_notification
            akd.save()

        if messages:
            request_body = {
                'messages': messages
            }
            with requests.Session() as s:
                try:
                    proxies = {'http': 'http://192.168.145.2:3128'}
                    response = s.post(auth=HTTPBasicAuth('karantinuz', 'AB6ciQvf'),
                                      url=f'{SMS_NOTIFICATION_API_BASE_URL}send',
                                      json=request_body,
                                      proxies=proxies)
                except:
                    for correct_sms_notification in correct_sms_notifications:
                        correct_sms_notification.delete()
                    return

            if response.status_code != 200:
                for correct_sms_notification in correct_sms_notifications:
                    correct_sms_notification.delete()

    class Meta:
        verbose_name = 'АКД'
        verbose_name_plural = 'АКД'
        db_table = 'akd'
        ordering = ('-id',)
        default_permissions = ()

        permissions = (
            # republic
            ('list_republic_akd', f'Can list republic {verbose_name}'),
            ('view_republic_akd', f'Can View republic {verbose_name}'),

            # region
            ('list_region_akd', f'Can list region {verbose_name}'),
            ('view_region_akd', f'Can View region {verbose_name}'),

            # point
            ('add_point_akd', f'Can add point {verbose_name}'),

            # inspector
            ('delete_inspector_akd', 'Can delete inspector AKD'),
        )


class Transit(models.Model):
    ikr_shipment = models.OneToOneField(IKRShipment, on_delete=models.CASCADE, related_name='transit',
                                        verbose_name='Отгрузка ИКР')
    inspector = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Инспектор')
    number = models.CharField(max_length=15, unique=True, null=True, verbose_name='№')
    conclusion = models.TextField(verbose_name='Вывод', null=True)
    given_date = models.DateField(auto_now_add=True, verbose_name='Дано в')
    representative_full_name = models.CharField(max_length=150, null=True, blank=True,
                                                verbose_name='Представитель организации')
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    @property
    def products(self):
        return self.ikr_shipment.products

    def __str__(self):
        return str(self.added_at)

    class Meta:
        verbose_name = 'Подтверждение транзита'
        verbose_name_plural = 'Подтверждение транзита'
        db_table = 'transit'
        default_permissions = ()

        permissions = (
            # republic
            ('list_republic_transit', f'Can list republic {verbose_name}'),

            # region
            ('list_region_transit', f'Can list region {verbose_name}'),

            # point
            ('add_point_transit', f'Can add point {verbose_name}'),
            ('list_point_transit', f'Can list point {verbose_name}'),

            # inspector
            ('delete_inspector_transit', f'Can delete inspector {verbose_name}')
        )


class ExportFSSApplication(models.Model):
    request_number = models.CharField(max_length=25)
    transport_number = models.CharField(max_length=1000)
    exporter_tin = models.CharField(max_length=15)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, verbose_name='Region')
    json = JSONField(null=True, blank=True)
    inspector = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    status = models.IntegerField(choices=ApplicationStatuses.CHOICES, default=ApplicationStatuses.ONE_ZERO_ZERO,
                                 verbose_name='Состояния Обработки')
    is_active = models.BooleanField(default=True)
    received_at = models.DateTimeField(verbose_name='received time from GTK', null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.request_number

    @property
    def received_at_in_seconds(self):
        if self.received_at:
            return self.received_at.strftime("%d-%m-%Y %H:%M:%S")
        else:
            return self.received_at

    @property
    def added_at_in_seconds(self):
        if self.added_at:
            return self.added_at.strftime("%d-%m-%Y %H:%M:%S")
        else:
            return self.added_at

    @property
    def updated_at_in_seconds(self):
        if self.updated_at:
            return self.updated_at.strftime("%d-%m-%Y %H:%M:%S")
        else:
            return self.updated_at

    @property
    def processing_time_in_minutes(self):
        try:
            export_fss = self.export_fss
            if export_fss.is_approved:
                return int((export_fss.updated_at - self.added_at).total_seconds() / 60)
            else:
                return int((datetime.datetime.now() - self.added_at).total_seconds() / 60)
        except:
            return int((datetime.datetime.now() - self.added_at).total_seconds() / 60)

    @property
    def processing_time(self):
        processing_time_in_hours = int(self.processing_time_in_minutes / 60)
        processing_time_in_days = int(processing_time_in_hours / 24)
        spending_days = processing_time_in_days
        spending_hours = processing_time_in_hours - processing_time_in_days * 24
        return f'{spending_days} дней и {spending_hours} часы'

    class Meta:
        verbose_name = 'Applicant for Export FSS'
        verbose_name_plural = 'Applicants for Export FSSes'
        ordering = ['-pk']
        db_table = 'export_fss_applicant'


class ExportFSSApplicationStatusStep(models.Model):
    application = models.ForeignKey(ExportFSSApplication, on_delete=models.CASCADE, related_name='status_steps',
                                    verbose_name='Export FSS Application')
    status = models.IntegerField(choices=ApplicationStatuses.CHOICES, default=ApplicationStatuses.ONE_ZERO_ZERO,
                                 verbose_name='Status')
    description = models.CharField(max_length=500, verbose_name='Причина', null=True, blank=True)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Отправитель', null=True, blank=True)
    sender_name = models.CharField(max_length=200, null=True, blank=True)
    sender_phone = models.CharField(max_length=50, null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.description

    @property
    def sender_name_ru(self):
        if self.sender:
            return self.sender.name_ru
        else:
            return self.sender_name

    @property
    def sender_phone_number(self):
        if self.sender:
            return self.sender.phone
        else:
            return self.sender_phone

    class Meta:
        verbose_name = 'Export FSS Application Status Step'
        verbose_name_plural = 'Export FSS Application Status Steps'
        db_table = 'export_fss_application_status_step'
        ordering = ['pk']
        default_permissions = ()


class ExportFSS(models.Model):
    application = models.OneToOneField(ExportFSSApplication, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='export_fss')
    request_number = models.CharField(max_length=25)
    request_date = models.DateField(verbose_name='Дата заказа')
    registered_number = models.CharField(max_length=40, verbose_name='Регистрационный номер сертификата', null=True)

    number = models.CharField(unique=True, max_length=25, verbose_name='№')
    order_number = models.CharField(max_length=25, verbose_name='Order №', null=True, unique=True, blank=True)
    given_date = models.DateField(verbose_name='Выдано')

    exporter_name = models.CharField(max_length=150, verbose_name='Наименование экспортера', null=True, blank=True)
    exporter_country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='export_fsses_export')
    exporter_region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='export_fsses_export')
    exporter_address = models.CharField(max_length=300, verbose_name='Адрес экспортера', null=True, blank=True)
    exporter_type = models.IntegerField(choices=CustomerType.CHOICES, verbose_name='Exporter type')
    exporter_tin = models.CharField(verbose_name='ИНН заявителя', max_length=15, null=True, blank=True)
    exporter_phone = models.CharField(max_length=35, null=True, blank=True)
    exporter_representative_name = models.CharField(max_length=150, verbose_name='ПРЕДСТАВИТЕЛЬ', null=True, blank=True)

    importer_name = models.CharField(max_length=150)
    importer_country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='export_fsses_import')
    importer_address = models.CharField(max_length=300)
    entry_point = models.CharField(max_length=300, verbose_name='Declared point of entry', null=True, blank=True)

    transport_method = models.IntegerField(choices=TransPortTypes.choices,
                                           verbose_name='Наименование средства транспортировка')
    transport_number = models.CharField(max_length=1000, verbose_name='Номер транспортного средства', null=True,
                                        blank=True)
    additional_declaration = models.TextField(verbose_name='Additional declaration', null=True, blank=True)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, verbose_name='Региона учреждения издателя сертификата',
                               null=True, blank=True)
    point = models.ForeignKey(Point, on_delete=models.CASCADE, verbose_name='Наименование пункта назначения', null=True,
                              blank=True, related_name='fsses')
    treatment_method = models.CharField(max_length=4000, verbose_name='Treatment  method', null=True, blank=True)
    chemical = models.CharField(max_length=150, verbose_name='Chemical (active ingredient)', null=True, blank=True)
    duration_and_temperature = models.CharField(max_length=256, verbose_name='Duration and temperature', null=True,
                                                blank=True)
    concentration = models.CharField(max_length=150, verbose_name='Concentration', null=True, blank=True)
    disinfected_date = models.CharField(max_length=256, verbose_name='Concentration', null=True, blank=True)
    extra_info = models.CharField(max_length=1500, verbose_name='Fumigation extra info', null=True,
                                  blank=True)
    fumigation_number = models.CharField(max_length=15, verbose_name='НОМЕР АКТ ФУМИГАЦИИ', null=True, blank=True)
    language = models.IntegerField(choices=Languages.CHOICES, verbose_name='Язык сертификата',
                                   default=Languages.RUSSIAN)
    inspector = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    inspector_name = models.CharField(null=True, blank=True, max_length=50)
    payment_amount = models.IntegerField(default=settings.ONE_BASIC_ESTIMATE)
    is_approved = models.BooleanField(verbose_name='Одобрить да или нет', default=False)
    sms_notification = models.OneToOneField(SMSNotification, on_delete=models.SET_NULL, null=True, blank=True,
                                            related_name='export_fss')
    is_synchronised = models.BooleanField(default=False)
    synchronisation_status = models.IntegerField(choices=SynchronisationStatus.choices,
                                                 default=SynchronisationStatus.not_synchronised)
    is_marked = models.BooleanField(verbose_name='Обозначение ярлыка идентификации', default=True)
    local_fss_number = models.CharField(max_length=25, verbose_name='Local FSS', null=True, blank=True)
    is_active = models.BooleanField(verbose_name='Active Export FSS', default=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    ephyto = JSONField(null=True, blank=True)

    all_objects = models.Manager()
    objects = IsApprovedManager()
    unapproved_objects = IsUnapprovedManager()

    def __str__(self):
        return f'№{self.number} {self.importer_name}'

    @property
    def created_time(self):
        return self.added_at.strftime("%d-%m-%Y %H:%M:%S")

    @property
    def inspector_fullname(self):
        inspector_name = ''
        if self.inspector:
            if self.language == Languages.ENGLISH:
                inspector_name = self.inspector.name_en
            else:
                inspector_name = self.inspector.name_ru
            inspector_name = inspector_name.split()
            if inspector_name[1][0] == 'S' and inspector_name[1][1] == 'h':
                inspector_name = str(inspector_name[0] + ' ' + inspector_name[1][0] + inspector_name[1][1])
            else:
                inspector_name = str(inspector_name[0] + ' ' + inspector_name[1][0])
        return self.inspector_name if self.inspector_name else inspector_name

    @staticmethod
    def send_sms():
        fsses = ExportFSS.objects.filter(sms_notification__isnull=True)
        messages = []
        correct_sms_notifications = []
        for fss in fsses:
            all_digits = re.findall(r'\d+', fss.exporter_phone)
            receiver_phone = "".join(all_digits)[-9:]
            exporter_name = (fss.exporter_name if not len(fss.exporter_name) >= 15 else
                             fss.exporter_name[0:15] + '...') if fss.exporter_name else ''
            tin = f"STIR: {fss.exporter_tin}\n" if fss.exporter_tin else f"Tashkilot nomi: {exporter_name}\n"
            text = "Uzdavkarantin inspeksiyasi\n" \
                   "Fitosanitar sertifikat\n" \
                   f"№ {fss.number}\n" \
                   f"{tin}" \
                   f"Transport: {TransPortTypes.local_names.get(fss.transport_method)}({fss.transport_number})\n" \
                   f"Export: {fss.importer_country.name_local}\n" \
                   f"Berilgan sanasi: {fss.given_date.strftime('%d.%m.%Y')}\n" \
                   f"Ko\'rish: http://efito.uz:30080/check_certificate?type=export_fss&number={fss.number}"
            sms_notification = SMSNotification.objects.create(
                text=text,
                receiver_phone=receiver_phone,
                purpose=SMSNotificationPurposes.EXPORT_FSS
            )
            if len(receiver_phone) == 9:
                sms_notification.status = SMSNotificationStatuses.REQUESTED
                sms_notification.save()
                messages.append({
                    'recipient': f'998{receiver_phone}',
                    'message-id': sms_notification.message_id,
                    'sms': {
                        'originator': SMS_NOTIFICATION_ORIGINATOR,
                        'content': {
                            'text': text
                        }
                    }
                })
                correct_sms_notifications.append(sms_notification)
            else:
                sms_notification.status = SMSNotificationStatuses.WRONG_NUMBER
                sms_notification.save()

            fss.sms_notification = sms_notification
            fss.save()

        if messages:
            request_body = {
                'messages': messages
            }
            with requests.Session() as s:
                try:
                    proxies = {'http': 'http://192.168.145.2:3128'}
                    response = s.post(auth=HTTPBasicAuth('karantinuz', 'AB6ciQvf'),
                                      url=f'{SMS_NOTIFICATION_API_BASE_URL}send',
                                      json=request_body,
                                      proxies=proxies)
                except:
                    for correct_sms_notification in correct_sms_notifications:
                        correct_sms_notification.delete()
                    return

            if response.status_code == 200:
                for correct_sms_notification in correct_sms_notifications:
                    correct_sms_notification.delete()


    class Meta:
        verbose_name = 'Export FSS'
        verbose_name_plural = 'Export FSS'
        db_table = 'export_fss'
        ordering = ['-pk']

        permissions = (
            # republic
            ('list_republic_fss', f'Can list republic {verbose_name}'),
            ('view_republic_fss', f'Can view republic {verbose_name}'),

            # region
            ('list_region_fss', f'Can list region {verbose_name}'),
            ('add_region_fss', f'Can add region {verbose_name}'),

            # point
            # ('list_point_fss', f'Can list point {verbose_name}'),
            # ('add_point_fss', f'Can add point {verbose_name}'),
        )


class ExportFSSProduct(models.Model):
    fss = models.ForeignKey(ExportFSS, on_delete=models.CASCADE, related_name='products', verbose_name='ExportFSS')
    name = models.CharField(max_length=500, verbose_name='Наименование товара')
    botanic_name = models.CharField(max_length=500, null=True, blank=True)
    hs_code = models.ForeignKey(HSCode, on_delete=models.CASCADE, verbose_name='KOD TN ved')

    manufactured_country = models.ForeignKey(Country, on_delete=models.CASCADE)
    manufactured_region = models.ForeignKey(Region, on_delete=models.CASCADE, null=True, blank=True)
    manufactured_district_code = models.CharField(max_length=10, null=True, blank=True)
    manufactured_district_name = models.CharField(max_length=128, null=True, blank=True)
    net_quantity = models.DecimalField(max_digits=11, decimal_places=3, verbose_name='aniq og\'irlik')
    net_quantity_unit = models.ForeignKey(Unit, on_delete=models.CASCADE, verbose_name=' aniq og\'irlik Единица',
                                          related_name='fss_product_net')
    gross_quantity = models.DecimalField(max_digits=11, decimal_places=3, verbose_name='yalpi og\'irlik')
    gross_quantity_unit = models.ForeignKey(Unit, on_delete=models.CASCADE, verbose_name='yalpi og\'irlik Единица',
                                            related_name='fss_product_gross')
    package_quantity = models.DecimalField(max_digits=11, decimal_places=3, null=True, blank=True,
                                           verbose_name='Количество упаковки продукции')
    package_quantity_unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='fss_product_package',
                                              verbose_name='Единица Количество упаковки продукции', null=True,
                                              blank=True)
    extra_package_quantity = models.DecimalField(max_digits=11, decimal_places=3, null=True, blank=True,
                                                 verbose_name='Количество упаковки продукции')
    extra_package_quantity_unit = models.ForeignKey(Unit, on_delete=models.CASCADE,
                                                    verbose_name='Единица Количество упаковки продукции', null=True,
                                                    blank=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.name

    @property
    def quantity(self):
        return self.net_quantity if self.net_quantity else self.gross_quantity

    @property
    def unit(self):
        return self.net_quantity_unit.name_ru if self.net_quantity_unit else self.gross_quantity_unit.name_ru

    class Meta:
        verbose_name = 'FSS продукт'
        verbose_name_plural = 'FSS продукты'
        db_table = 'export_fss_product'
        default_permissions = ()


class ImportFSS(models.Model):
    number = models.CharField(unique=True, max_length=50, verbose_name='№')

    given_date = models.DateField(verbose_name='Выдано')

    exporter_name = models.CharField(max_length=150, verbose_name='Наименование экспортера', null=True,
                                     blank=True)
    exporter_country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='import_fsses_export')
    exporter_address = models.CharField(max_length=300, verbose_name='Адрес экспортера', null=True, blank=True)

    importer_name = models.CharField(max_length=150, verbose_name='Ф.И.О. заявителя')
    importer_country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='import_fsses_import')
    importer_address = models.CharField(max_length=300, verbose_name='Адрес заявителя')

    transport_method = models.CharField(max_length=128, verbose_name='Наименование средства транспортировка')
    transport_number = models.CharField(max_length=256, verbose_name='Номер транспортного средства',
                                        null=True, blank=True)

    disinfected_date = models.DateField(verbose_name='Date', default=None, null=True, blank=True)
    treatment_method = models.CharField(max_length=256, verbose_name='Treatment  method', null=True, blank=True)
    chemical = models.CharField(max_length=256, verbose_name='Chemical (active ingredient)', null=True, blank=True)
    duration_and_temperature = models.CharField(max_length=256, verbose_name='Duration and temperature', null=True,
                                                blank=True)
    concentration = models.CharField(max_length=256, verbose_name='Concentration', null=True, blank=True)
    extra_info = models.CharField(max_length=1500, verbose_name='Extra info', null=True, blank=True)
    api_user = models.ForeignKey(APIUser, on_delete=models.DO_NOTHING, null=True)
    api_data = JSONField(null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return f'№{self.number} {self.importer_name}'

    class Meta:
        verbose_name = 'Import FSS'
        verbose_name_plural = 'Import FSS'
        db_table = 'import_fss'
        ordering = ('given_date', '-id')

        permissions = (
            # republic
            ('list_import_fss', f'List {verbose_name}'),
        )


class ImportFSSProduct(models.Model):
    fss = models.ForeignKey(ImportFSS, on_delete=models.CASCADE, related_name='products', verbose_name='ExportFSS')
    name = models.CharField(max_length=500, verbose_name='Наименование товара')
    botanic_name = models.CharField(max_length=500, null=True, blank=True)
    hs_code = models.CharField(max_length=15, verbose_name='KOD TN ved', default='')

    manufactured_country = models.ForeignKey(Country, on_delete=models.CASCADE, null=True,
                                             blank=True, related_name='import_fss_products')
    manufactured_address = models.CharField(max_length=300, null=True, blank=True)

    net_quantity = models.DecimalField(max_digits=11, decimal_places=3, verbose_name='Aniq og\'irlik', null=True,
                                       blank=True)
    net_quantity_unit = models.CharField(max_length=50, null=True, blank=True)

    gross_quantity = models.DecimalField(max_digits=11, decimal_places=3, verbose_name='Yalpi og\'irlik', null=True,
                                         blank=True)
    gross_quantity_unit = models.CharField(max_length=50, null=True, blank=True)

    package_quantity = models.DecimalField(max_digits=11, decimal_places=3, null=True, blank=True,
                                           verbose_name='Количество упаковки продукции')
    package_quantity_unit = models.CharField(max_length=50, null=True, blank=True)

    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.name

    @property
    def quantity(self):
        return self.net_quantity if self.net_quantity else self.gross_quantity

    @property
    def unit(self):
        return self.net_quantity_unit if self.net_quantity_unit else self.gross_quantity_unit

    class Meta:
        verbose_name = 'Import FSS продукт'
        verbose_name_plural = 'FSS продукты'
        db_table = 'import_fss_product'
        default_permissions = ()


class GivenBlanks(models.Model):
    blank_type = models.IntegerField(choices=BlankTypes.CHOICES, default=BlankTypes.LocalFSS)
    first_blank_number = models.PositiveIntegerField(verbose_name='first_blank_number', unique=True)
    last_blank_number = models.PositiveIntegerField(verbose_name='last_blank_number', unique=True)
    number_of_blanks = models.PositiveSmallIntegerField(verbose_name='number_of_blanks')
    region = models.ForeignKey(Region, on_delete=models.CASCADE, verbose_name='Точка регистрации', default=None)
    inspector = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Inspector',
                                  related_name='given_local_fsses')
    registrar = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='кладовщик', related_name='given_blanks')
    added_at = models.DateTimeField(auto_now_add=True, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return str(self.first_blank_number) + " - " + str(self.last_blank_number)

    class Meta:
        verbose_name = 'GivenBlank'
        verbose_name_plural = 'GivenBlanks'
        db_table = 'given_blanks'
        get_latest_by = 'added_at'
        ordering = ('-added_at',)
        default_permissions = ()

        permissions = (
            # republic
            ('list_republic_given_blanks', f'Can list republic {verbose_name}'),
            ('add_republic_given_blanks', f'Can add republic {verbose_name}'),
            ('delete_republic_given_blanks', f'Can delete republic {verbose_name}'),

            # region
            ('list_region_given_blanks', f'Can list region {verbose_name}'),
            ('add_region_given_blanks', f'Can add region {verbose_name}'),
            ('delete_region_given_blanks', f'Can delete region {verbose_name}'),
        )


class LocalFSSApplication(models.Model):
    request_number = models.CharField(unique=True, max_length=50, verbose_name='Номер заявки')
    request_date = models.DateField(verbose_name='Дата заявления')
    applicant_type = models.IntegerField(choices=CustomerType.CHOICES, verbose_name='Налогоплательщик')
    applicant_tin = models.CharField(verbose_name='ИНН', max_length=15)
    applicant_name = models.CharField(max_length=155, verbose_name='Наименование заявителя/организации')
    applicant_region = models.ForeignKey(Region, on_delete=models.DO_NOTHING, verbose_name='регион', related_name='local_fss_applicants')
    applicant_address = models.CharField(max_length=300, verbose_name='Адрес')
    transport_number = models.CharField(max_length=50, null=True, blank=True)
    applicant_phone = models.CharField(max_length=35, verbose_name='Телефон')
    manufactured_region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='manufactured_region_in_local_fss_application')
    manufactured_district = models.ForeignKey(District, on_delete=models.CASCADE, related_name='manufactured_district_in_local_fss_application')
    sender_region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='sender_region_in_local_fss_application', verbose_name='sender_region')
    sender_district = models.ForeignKey(District, on_delete=models.CASCADE, related_name='sender_district_in_local_fss_application', verbose_name='sender_district')
    status = models.IntegerField(choices=ApplicationStatuses.CHOICES, default=ApplicationStatuses.ONE_ZERO_ZERO,
                                 verbose_name='Состояния Обработки')
    fumigation_number = models.CharField(verbose_name='fumigation_number', max_length=15, null=True, blank=True)
    fumigation_given_date = models.DateField(verbose_name='Выдано', null=True, blank=True)
    type = models.IntegerField(choices=ImpExpLocChoices.CHOICES, default=ImpExpLocChoices.Local)
    field_id = models.PositiveIntegerField(verbose_name='Dala raqami', null=True, blank=True)
    products = JSONField(default=dict)
    inspector = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_paid = models.BooleanField(default=False)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return str(self.request_number)

    class Meta:
        verbose_name = 'Application for Local FSS'
        verbose_name_plural = 'Applications for Local FSS'
        ordering = ['pk']
        db_table = 'local_fss_application'
        default_permissions = ()

        permissions = (
            ('can_list_local_fss_application', f'Can list {verbose_name}'),
            ('can_approve_local_fss_application', f'Can approve {verbose_name}')
        )


class LocalFSSApplicationStatusStep(models.Model):
    application = models.ForeignKey(LocalFSSApplication, on_delete=models.CASCADE, related_name='status_steps',
                                    verbose_name='Local FSS Application')
    status = models.IntegerField(choices=ApplicationStatuses.CHOICES, default=ApplicationStatuses.ONE_ZERO_ZERO,
                                 verbose_name='Status')
    description = models.CharField(max_length=500, verbose_name='Причина', null=True, blank=True)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Отправитель', null=True, blank=True)
    sender_name = models.CharField(max_length=200, null=True, blank=True)
    sender_phone = models.CharField(max_length=50, null=True, blank=True)
    sent_data = JSONField(default=dict, null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.description

    @property
    def sender_name_ru(self):
        if self.sender:
            return self.sender.name_local
        else:
            return self.sender_name

    @property
    def sender_phone_number(self):
        if self.sender:
            return self.sender.phone
        else:
            return self.sender_phone

    class Meta:
        verbose_name = 'Local FSS Application Status Step'
        verbose_name_plural = 'Local FSS Application Status Steps'
        db_table = 'local_fss_application_status_step'
        ordering = ['pk']
        default_permissions = ()


class LocalFSS(models.Model):
    given_blanks = models.ForeignKey(GivenBlanks, on_delete=models.CASCADE,
                                     related_name='local_fsses', verbose_name='LocalFSS', null=True, blank=True)
    application = models.OneToOneField(LocalFSSApplication, on_delete=models.SET_NULL, related_name='local_fss',
                                       verbose_name='Application', null=True, blank=True)
    number = models.CharField(unique=True, max_length=15, verbose_name='LocalFSS №')
    given_date = models.DateField(verbose_name='Выдано')
    expire_date = models.DateField(verbose_name='Выдано', null=True, blank=True)
    applicant_tin = models.CharField(verbose_name='ИНН заявителя', max_length=15, blank=True)
    applicant_name = models.CharField(max_length=155, verbose_name='Ф.И.О. заявителя')
    applicant_address = models.CharField(max_length=310, verbose_name='Адрес экспортера', null=True, blank=True)
    applicant_phone = models.CharField(max_length=13, null=True, blank=True)
    transport_number = models.CharField(max_length=50, null=True, blank=True, default='')
    manufactured_region = models.ForeignKey(Region, on_delete=models.CASCADE)
    manufactured_district = models.ForeignKey(District, on_delete=models.CASCADE)
    sender_region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='sender_region',
                                      verbose_name='sender_region')
    sender_district = models.ForeignKey(District, on_delete=models.CASCADE, related_name='sender_district',
                                        verbose_name='sender_district')
    receiver_region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='receiver_region',
                                        verbose_name='receiver_region', null=True, blank=True)
    fumigation_number = models.CharField(verbose_name='fumigation_number', max_length=15, null=True, blank=True)
    fumigation_given_date = models.DateField(verbose_name='Выдано', null=True, blank=True)
    payment_amount = models.DecimalField(verbose_name='Сумма платежа', max_digits=10, decimal_places=2)
    is_paid = models.BooleanField(default=False, verbose_name='Paid')
    type = models.IntegerField(choices=ImpExpLocChoices.CHOICES, default=ImpExpLocChoices.Local)
    field_id = models.PositiveIntegerField(verbose_name='Dala raqami', null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    inspector = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Inspector')

    def __str__(self):
        return str(self.number)

    def can_edit(self, user):
        if user.has_perm('exim.edit_republic_local_fss') and self.application is None and \
                (datetime.datetime.now() - self.added_at).total_seconds() < 86400:
            return True
        else:
            return False

    @property
    def get_absolute_url(self):
        return "https://efito.uz/fss/local/" + str(self.number) + "/print"

    @property
    def created_time(self):
        return self.added_at.strftime("%d-%m-%Y %H:%M:%S")

    class Meta:
        verbose_name = 'LocalFSS'
        verbose_name_plural = 'LocalFSS'
        db_table = 'local_fss'
        ordering = ('number',)
        default_permissions = ()

        permissions = (
            # republic
            ('list_republic_local_fss', f'Can list republic {verbose_name}'),
            ('view_republic_local_fss', f'Can View republic {verbose_name}'),
            ('edit_republic_local_fss', f'Can Edit republic {verbose_name}'),

            # region
            ('list_region_local_fss', f'Can list region {verbose_name}'),
            ('view_region_local_fss', f'Can View region {verbose_name}'),
            ('add_region_local_fss', f'Can Add region {verbose_name}'),
            ('delete_region_local_fss', f'Can Delete region {verbose_name}'),

            # inspector
            ('list_local_fss', f'Can list {verbose_name}'),
            ('add_local_fss', f'Can Add {verbose_name}'),
            ('delete_local_fss', f'Can Delete {verbose_name}'),
        )


class LocalFSSProduct(models.Model):
    local_fss = models.ForeignKey(LocalFSS, on_delete=models.CASCADE, related_name='products', verbose_name='LocalFSS')
    name = models.CharField(max_length=555, verbose_name='Наименование товара')
    hs_code = models.ForeignKey(HSCode, on_delete=models.CASCADE, verbose_name='KOD TN ved')
    quantity = models.FloatField(default=0.0, verbose_name='Количество')
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, verbose_name='Единица', null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'LocalFSS продукт'
        verbose_name_plural = 'LocalFSS продукты'
        db_table = 'local_fss_product'
        default_permissions = ()


class LocalFSSImage(models.Model):
    local_fss = models.ForeignKey(LocalFSS, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='exim/local_fss/')
    added_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def url(self):
        return os.path.join('/', settings.MEDIA_URL, 'exim/local_fss/' + os.path.basename(str(self.image.url)))


class SURSystem(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE, verbose_name='Давлат')
    farm = models.CharField(max_length=250, verbose_name='Экиш материалларини етиштирувчи питомник номи')
    exporter_name = models.CharField(max_length=250, verbose_name='Экспортёр номи', null=True, blank=True)
    registered_date = models.DateField(verbose_name='Аттестацияўтказилган вақт')
    is_allowed = models.BooleanField(default=False, verbose_name='Фитосанитария талабларга мувофиқ ҳудуд')
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.farm

    class Meta:
        verbose_name = 'SUR system'
        verbose_name_plural = 'SUR system'
        db_table = 'sur_system'
        ordering = ('-id',)


class SURSystemHSCode(models.Model):
    sur_system = models.ForeignKey(SURSystem, on_delete=models.CASCADE, related_name='hs_codes',
                                   verbose_name='Вредитель')
    hs_code = models.ForeignKey(HSCode, on_delete=models.CASCADE, verbose_name='Код ТН ВЭД')
    description = models.CharField(max_length=500, verbose_name='Маҳсулотноми/нави', null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        verbose_name = 'Код ТН ВЭД'
        verbose_name_plural = 'Код ТН ВЭД'
        db_table = 'sur_system_hs_code'


class Pest(models.Model):
    latin_name = models.TextField(unique=True, verbose_name='Латинское название', null=True)
    name_ru = models.TextField(unique=True, blank=True,
                               verbose_name='Название и краткое описание вредного организма, имеющего')
    damaged_plants_in_ru = models.TextField(null=True, blank=True, verbose_name='Повреждаемые растения')
    damaged_plant_parts_in_ru = models.TextField(null=True, blank=True, verbose_name='Повреждаемые части растений')
    penetrating_ways_in_ru = models.TextField(null=True, blank=True,
                                              verbose_name='Вероятность путей проникновения ВО при импорте '
                                                           'подкарантинной продукции в Республику Узбекистан')
    note_ru = models.TextField(null=True, blank=True)
    name_uz = models.TextField(null=True, blank=True,
                               verbose_name='Ўзбекистон Республикаси учун карантин аҳамиятга эга бўлган '
                                            'зарарли организмларнинг номланиши ва қисқача таърифи')
    damaged_plants_in_uz = models.TextField(null=True, blank=True, verbose_name='Зарарланадиган ўсимликлар')
    damaged_plant_parts_in_uz = models.TextField(null=True, blank=True, verbose_name='Зарарланадиган ўсимлик аъзолари')
    penetrating_ways_in_uz = models.TextField(null=True, blank=True,
                                              verbose_name='Ўзбекистон Республикаси учун карантин аҳамиятга эга бўлган '
                                                           'зарарли организмни кириб келиши мумкин бўлган йўллари')
    note_uz = models.TextField(null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.name_ru

    class Meta:
        verbose_name = 'Информация о вредных организмах имеющих карантинное значение для РУз'
        verbose_name_plural = 'Информация о вредных организмах имеющих карантинное значение для РУз'
        db_table = 'pest'
        ordering = ('-id',)


class PestDistributedCountry(models.Model):
    pest = models.ForeignKey(Pest, on_delete=models.CASCADE, related_name='countries', verbose_name='Вредитель')
    country = models.ForeignKey(Country, on_delete=models.CASCADE, verbose_name='Страна')
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.country.name_ru

    class Meta:
        verbose_name = 'Распространение карантинного вредного организма по странам'
        verbose_name_plural = 'Распространение карантинного вредного организма по странам'
        db_table = 'pest_distributed_country'


class PestHSCode(models.Model):
    pest = models.ForeignKey(Pest, on_delete=models.CASCADE, related_name='hs_codes', verbose_name='Вредитель')
    hs_code = models.CharField(max_length=10, verbose_name='Код ТН ВЭД')
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.hs_code

    class Meta:
        verbose_name = 'Код ТН ВЭД'
        verbose_name_plural = 'Код ТН ВЭД'
        db_table = 'pest_hs_code'


class PestImage(models.Model):
    pest = models.ForeignKey(Pest, on_delete=models.CASCADE, related_name='images', verbose_name='Вредитель')
    image = models.ImageField(upload_to='pest/', verbose_name='Картинка')
    description = models.TextField(null=True, blank=True, verbose_name='Описание')
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def url(self):
        return os.path.join('/', settings.MEDIA_URL, 'pest/' + os.path.basename(str(self.image.url)))

    def image_tag(self):
        # used in the admin site model as a "thumbnail"
        return mark_safe('<img src="{}" width="150" height="150" />'.format(self.url()))

    image_tag.short_description = 'Image'

    class Meta:
        verbose_name = 'Пример изображения'
        verbose_name_plural = 'Примеры изображений'
        db_table = 'pest_image'


class WrongIKR(models.Model):
    ikr = JSONField(verbose_name='IKR')
    exception_details = models.TextField(null=True)
    action = models.IntegerField(choices=APIAction.CHOICES, default=APIAction.UNKNOWN)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return str(self.pk)

    class Meta:
        verbose_name = 'wrong ikr'
        verbose_name_plural = 'wrong ikrs'
        db_table = 'wrong_ikr'
        default_permissions = ()


class WrongAKD(models.Model):
    tried_json = JSONField(verbose_name='AKD')
    description = models.TextField(null=True)
    trials_count = models.IntegerField(default=1)
    error_type = models.IntegerField(choices=WrongAKDErrorTypes.ERROR_TYPES)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return str(self.pk)

    class Meta:
        verbose_name = 'wrong akds'
        verbose_name_plural = 'wrong akds'
        db_table = 'wrong_akd'
        default_permissions = ()


class WrongExportFSS(models.Model):
    json = JSONField(verbose_name='FSS', unique=True)
    exception_details = models.TextField(null=True)
    action = models.IntegerField(choices=APIAction.CHOICES, default=APIAction.UNKNOWN)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return str(self.pk)

    class Meta:
        verbose_name = 'wrong FSS'
        verbose_name_plural = 'wrong FSSes'
        db_table = 'wrong_export_fss'
        default_permissions = ()


class OldAKD(models.Model):
    json = JSONField()
    sw_id = models.BigIntegerField(null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    sms_notification = models.OneToOneField(SMSNotification, on_delete=models.SET_NULL, null=True, blank=True,
                                            related_name='old_akd')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return str(self.pk)

    def save(self, *args, **kwargs):
        if not self.pk:
            super(OldAKD, self).save()
        if not self.sw_id:
            self.sw_id = 100000000000 + self.pk

        super(OldAKD, self).save()

    @staticmethod
    def send_sms():
        akds = OldAKD.objects.filter(sms_notification__isnull=True)
        messages = []
        correct_sms_notifications = []
        for akd in akds:
            akd_json = akd.json
            akd_number = akd_json.get('FMD_NO')
            akd_number = akd_number if akd_number else akd_json.get('CRPP_NO')
            all_digits = re.findall(r'\d+', akd_json.get('IMPPN_TELNO'))
            receiver_phone = "".join(all_digits)[-9:]
            importer_name = akd_json.get('IMPPN_NM')
            importer_name = (importer_name if not len(importer_name) >= 15 else
                             importer_name[0:15] + '...') if importer_name else ''
            tin = akd_json.get('IMPPN_TXPR_UNIQ_NO')
            tin = f"STIR: {tin}\n" if tin else f"Tashkilot nomi: {importer_name}\n"
            try:
                given_date = f"Berilgan sanasi: {datetime.datetime.strptime(akd_json.get('CRPP_VALT_PRID_STRT_DT'), '%Y-%m-%d').strftime('%d.%m.%Y')}"
            except:
                given_date = ''
            text = "Uzdavkarantin inspeksiyasi\n" \
                   "Karantin kurigi dalolatnomasi\n" \
                   f"№ {akd_number}\n" \
                   f"{tin}" \
                   f"{given_date}" \
                # f"Ko\'rish: http://efito.uz:30080/check_certificate?type=akd&number={akd_number}"
            sms_notification = SMSNotification.objects.create(
                text=text,
                receiver_phone=receiver_phone,
                purpose=SMSNotificationPurposes.OLD_AKD
            )
            if len(receiver_phone) == 9:
                sms_notification.status = SMSNotificationStatuses.REQUESTED
                sms_notification.save()
                messages.append({
                    'recipient': f'998{receiver_phone}',
                    'message-id': sms_notification.message_id,
                    'sms': {
                        'originator': SMS_NOTIFICATION_ORIGINATOR,
                        'content': {
                            'text': text
                        }
                    }
                })
                correct_sms_notifications.append(sms_notification)
            else:
                sms_notification.status = SMSNotificationStatuses.WRONG_NUMBER
                sms_notification.save()

            akd.sms_notification = sms_notification
            akd.save()

        if messages:
            request_body = {
                'messages': messages
            }
            with requests.Session() as s:
                try:
                    # proxies = {'http': 'http://192.168.145.2:3128'}
                    response = s.post(auth=HTTPBasicAuth('karantinuz', 'AB6ciQvf'),
                                      url=f'{SMS_NOTIFICATION_API_BASE_URL}send',
                                      json=request_body)
                    # proxies=proxies)
                except:
                    for correct_sms_notification in correct_sms_notifications:
                        correct_sms_notification.delete()
                    return

            if response.status_code != 200:
                for correct_sms_notification in correct_sms_notifications:
                    correct_sms_notification.delete()

    class Meta:
        verbose_name = 'Old AKD Json Version'
        verbose_name_plural = 'Old AKD Json Version'
        db_table = 'old_akd'
        default_permissions = ()


class JsonIKR(models.Model):
    ikr = models.OneToOneField(IKR, on_delete=models.CASCADE, related_name='json')
    json = JSONField(null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return str(self.pk)

    class Meta:
        verbose_name = 'IKR JSON version'
        verbose_name_plural = 'IKRs JSON version'
        db_table = 'json_ikr'
        default_permissions = ()


class JsonExportFSS(models.Model):
    fss = models.OneToOneField(ExportFSS, on_delete=models.CASCADE, related_name='json')
    json = JSONField(null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return str(self.pk)

    class Meta:
        verbose_name = 'FSS JSON version'
        verbose_name_plural = 'FSSes JSON version'
        db_table = 'json_export_fss'
        default_permissions = ()


class WrongApplication(models.Model):
    json = JSONField(verbose_name='Application')
    exception_details = models.TextField(null=True)
    application_type = models.IntegerField(choices=ApplicationTypes.CHOICES, default=ApplicationTypes.IKR)
    action = models.IntegerField(choices=APIAction.CHOICES, default=APIAction.UNKNOWN)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return str(self.pk)

    class Meta:
        verbose_name = 'Wrong Application'
        verbose_name_plural = 'Wrong Applications'
        db_table = 'wrong_application'


class TemporarilyStoppedShipment(models.Model):
    number = models.CharField(max_length=9, unique=True)
    transport_number = models.CharField(max_length=90)
    importer_type = models.IntegerField(choices=CustomerType.CHOICES)
    importer_tin = models.CharField(max_length=9)
    importer_name = models.CharField(max_length=155)
    importer_region = models.ForeignKey(Region, on_delete=models.DO_NOTHING)
    exporter_name = models.CharField(max_length=155)
    exporter_country = models.ForeignKey(Country, on_delete=models.CASCADE)
    transport_method = models.IntegerField(choices=TransPortTypes.choices)
    point = models.ForeignKey(Point, on_delete=models.DO_NOTHING)
    ikr_number = models.CharField(max_length=1000, null=True, blank=True)
    ikr_given_date = models.DateField(null=True, blank=True)
    fss_number = models.CharField(max_length=1000, null=True, blank=True)
    fss_given_date = models.DateField(null=True, blank=True)
    fss_file = models.FileField(null=True, blank=True, upload_to='temporarily_stopped_shipment_fsses/')
    reason_of_stopping = models.CharField(max_length=512)
    implemented_actions = models.CharField(max_length=512)
    final_result = models.CharField(max_length=512, null=True, blank=True)
    is_transit = models.BooleanField(default=False)
    status = models.IntegerField(choices=TemporarilyStoppedShipmentStatuses.CHOICES, default=TemporarilyStoppedShipmentStatuses.ON_PROCESS)
    inspection_general = models.CharField(max_length=50, default='И.К.Эргашев')
    regional_inspection_general = models.ForeignKey(User, on_delete=models.CASCADE, related_name='regional_inspection_general')
    sent_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='temporarily_stopped_shipments_senders')
    approved_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='temporarily_stopped_shipments_approvers', null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    @property
    def is_on_time(self):
        return self.added_at + datetime.timedelta(seconds=TIME_FOR_TEMPORARILY_STOPPED_SHIPMENT) > timezone.now()

    class Meta:
        verbose_name = 'Temporarily Stopped Shipment'
        verbose_name_plural = 'Temporarily Stopped Shipments'
        db_table = 'temporarily_stopped_shipment'
        get_latest_by = 'added_at'
        ordering = ('-added_at',)
        default_permissions = ()

        permissions = (
            # republic
            ('list_republic_temporarily_stopped_shipments', f'Can list republic {verbose_name}'),

            # region
            ('list_region_temporarily_stopped_shipments', f'Can list region {verbose_name}'),

            # point
            ('list_point_temporarily_stopped_shipment', f'Can list point {verbose_name}'),
            ('add_temporarily_stopped_shipment', f'Can add {verbose_name}'),
        )


class TemporarilyStoppedShipmentProduct(models.Model):
    temporarily_stopped_shipment = models.ForeignKey(TemporarilyStoppedShipment, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=500)
    quantity = models.FloatField()
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Temporarily Stopped Shipment Product'
        verbose_name_plural = 'Temporarily Stopped Shipment Products'
        db_table = 'temporarily_stopped_shipment_product'
        ordering = ['-pk']
        default_permissions = ()
