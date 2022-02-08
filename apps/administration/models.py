import json

import binascii
import html
import os
import uuid
from datetime import datetime

import requests
# from bot.utils import send_message
from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.safestring import mark_safe

from administration.managers import UserManager
from administration import statuses
from administration.statuses import SMSNotificationStatuses, SMSNotificationPurposes, IntegratedDataType, ContentTypes
from core.settings import proxy_config
from invoice.statuses import InvoiceServices
import telebot
bot = telebot.TeleBot('1812368506:AAE6sqpZewP178Fzrr-k4Bhqkl4TjZtZR_Y')
chat_id = -1001481223731


class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=15, unique=True)
    name_ru = models.CharField(max_length=50)
    name_en = models.CharField(max_length=50)
    name_local = models.CharField(max_length=50)
    tin = models.CharField(max_length=15, verbose_name='ИНН', unique=True, null=True, blank=True)
    phone = models.CharField(max_length=15)
    # photo = models.ImageField(upload_to='photo/user', null=True, blank=True)
    # role = models.IntegerField(choices=statuses.UserRoles.CHOICES, default=statuses.UserRoles.ROADWAY)
    point = models.ForeignKey('administration.Point', on_delete=models.CASCADE, null=True, blank=True)
    status = models.IntegerField(choices=statuses.UserStatuses.CHOICES, default=statuses.UserStatuses.ACTIVE)
    is_esi_required = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    added_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['phone']

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = 'Foydalanuvchi'
        verbose_name_plural = 'Foydalanuvchilar'
        db_table = 'user'

    def has_delete_permission(self):
        if self.status == statuses.UserStatuses.ONPROCESS:
            return True
        else:
            return False


class UserPoints(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='points')
    point = models.ForeignKey('administration.Point', on_delete=models.CASCADE,)
    is_active = models.BooleanField(verbose_name='IS Active', default=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)


ROLE_CHOICES = (
    (1, 'Ички ФСС расмийлаштириш'),
    (2, 'Эхпорт ФСС расмийлаштириш'),
    (3, 'Эхпорт ва Ички ФСС расмийлаштириш'),
    (4, 'АКД расмийлаштириш'),
    (5, 'АКД ва Эхпорт ФСС расмийлаштириш'),
    (6, 'АКД, Ички ва Эхпорт ФСС расмийлаштириш'),
    (7, 'Фумигация расмийлаштириш'),
    (8, 'Фумигация расмийлаштириш ҳамда химикатларни кирди/чиқди қилиш'),
    (9, 'Назорат қилиш(Барчасини)'),
    (10, 'Агентлик бошқарма бошлиғи'),
    (11, 'Ўчирилсин'),
)


class UserRegistrationRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='registration_requests')
    behest = models.FileField()
    chosen_role = models.IntegerField(choices=ROLE_CHOICES, null=True)
    role = models.CharField(max_length=500)
    responsible = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='responsible')
    is_active = models.BooleanField(verbose_name='IS Active', default=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def save(self, *args, **kwargs):
        if not self.pk:
            behest_extension = self.behest.name.split('.')[-1]
            behest_extension = behest_extension.lower()
            if behest_extension == 'pdf':
                self.behest.name = os.path.join('users', f'{uuid.uuid4()}.pdf')
                super(UserRegistrationRequest, self).save()
            else:
                raise Exception("Invalid format")
        else:
            super(UserRegistrationRequest, self).save()

    class Meta:
        verbose_name = 'User Registration Request'
        verbose_name_plural = 'User Registration Requests'
        db_table = 'user_registration_request'
        default_permissions = ()
        permissions = (
            ('can_register_region_user', f'Can register region user'),
            ('can_approve_registered_user', f'Can approve registered user')
        )


class Country(models.Model):
    code = models.CharField(max_length=5, verbose_name='Country code', unique=True)
    name_ru = models.CharField(max_length=100, verbose_name='Название на русском')
    name_en = models.CharField(max_length=100, verbose_name='Название на английском')
    name_local = models.CharField(max_length=100, verbose_name='Внутреннее название')
    gtk_code = models.CharField(max_length=15, null=True, blank=True,
                                verbose_name='GTK Код учреждения издателя сертификата')
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name_ru

    @property
    def name_uz_cyrillic(self):
        latin_to_cyrillic = settings.LATIN_TO_CYRILLIC
        name_uz_cyrillic = ''
        loop_counter = 0
        for i in self.name_local:
            index = ''
            if loop_counter + 1 < len(self.name_local):
                index = self.name_local[loop_counter] + self.name_local[loop_counter + 1]
            if len(latin_to_cyrillic.get(index, '')) > 0:
                loop_counter = loop_counter + 1
                name_uz_cyrillic = name_uz_cyrillic + latin_to_cyrillic.get(index, '')
            elif loop_counter < len(self.name_local):
                name_uz_cyrillic = name_uz_cyrillic + latin_to_cyrillic[self.name_local[loop_counter]]
            loop_counter = loop_counter + 1
        return html.unescape(name_uz_cyrillic)

    class Meta:
        verbose_name = 'Страна'
        verbose_name_plural = 'Страны'
        db_table = 'country'
        default_permissions = ()


class Region(models.Model):
    name_ru = models.CharField(max_length=256, verbose_name='Название на русском')
    name_en = models.CharField(max_length=256, verbose_name='Название на английском')
    name_local = models.CharField(max_length=256, verbose_name='Местное название')
    code = models.CharField(max_length=3, unique=True, blank=True)
    gtk_code = models.CharField(max_length=10, unique=True, null=True, blank=True)
    tin = models.CharField(max_length=15, null=True, unique=True, blank=True, verbose_name='ИНН')
    address = models.TextField(verbose_name='Inspection address', null=True, blank=True)
    phone = models.CharField(max_length=9, unique=True, null=True, blank=True, verbose_name='Inspection Phone')
    bank_account = models.CharField(max_length=27, null=True, blank=True, verbose_name='лицевой счет')
    settlement_account = models.CharField(max_length=20, verbose_name='Pасчетный Cчет', null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name_ru

    @property
    def agency_name_local(self):
        if self.pk in [1, 15]:
            return self.name_local
        else:
            return 'Ўсимликлар карантини ва ҳимояси агентлиги {} ўсимликлар карантини ва ҳимояси бошқармаси'.format(self.name_local)

    @property
    def point_name(self):
        return '{} Ўсимликлар Карантин Инспекцияси'.format(self.name_ru)

    class Meta:
        verbose_name = 'Регион'
        verbose_name_plural = 'Регионы'
        db_table = 'region'
        default_permissions = ()


class District(models.Model):
    region = models.ForeignKey(Region, on_delete=models.CASCADE, null=True, related_name='districts',
                               verbose_name='Область')
    name_ru = models.CharField(max_length=50, verbose_name='Название на русском')
    name_en = models.CharField(max_length=50, verbose_name='Название на английском')
    name_local = models.CharField(max_length=50, verbose_name='Местное название')
    code = models.CharField(max_length=10, null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name_ru

    class Meta:
        verbose_name = 'Район'
        verbose_name_plural = 'Районы'
        db_table = 'district'
        default_permissions = ()


# class Inspector(models.Model):
#     name_ru = models.CharField(max_length=50, verbose_name='Название на русском')
#     name_en = models.CharField(max_length=50, verbose_name='Название на английском')
#     name_local = models.CharField(max_length=50, verbose_name='Внутреннее название')
#     region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='inspectors')
#
#     def __str__(self):
#         return self.name_ru
#
#     class Meta:
#         verbose_name = 'Инспектор'
#         verbose_name_plural = 'Инспекторы'
#         db_table = 'inspector'


# class PointType(models.Model):
#     name_ru = models.CharField(max_length=100, verbose_name='Название на русском', null=True)
#     name_en = models.CharField(max_length=100, verbose_name='Название на английском', null=True)
#     name_local = models.CharField(max_length=100, verbose_name='Внутреннее название', null=True)
#
#     def __str__(self):
#         return self.name_ru
#
#     class Meta:
#         verbose_name = 'Point type'
#         verbose_name_plural = 'Point types'
#         db_table = 'point_type'


class Point(models.Model):
    code = models.CharField(max_length=10, null=True, blank=True, unique=True)
    name_ru = models.CharField(max_length=100, verbose_name='Название на русском', null=True)
    name_en = models.CharField(max_length=100, verbose_name='Название на английском', null=True)
    name_local = models.CharField(max_length=100, verbose_name='Внутреннее название', null=True)
    region = models.ForeignKey(Region, on_delete=models.DO_NOTHING, related_name='points', verbose_name='Регион',
                               null=True)
    type = models.IntegerField(choices=statuses.PointTypes.choices, default=statuses.PointTypes.ROADWAY)
    status = models.BooleanField(choices=statuses.PointStatuses.CHOICES, default=statuses.PointStatuses.ACTIVE,
                                 verbose_name='Активным или пассивным?')
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')

    def __str__(self):
        return str(self.code) + '-' + str(self.name_ru)

    class Meta:
        verbose_name = 'Point'
        verbose_name_plural = 'Points'
        db_table = 'point'
        default_permissions = ()


class Unit(models.Model):
    code = models.CharField(max_length=50, null=True, blank=True, verbose_name='GTKCode')
    name_ru = models.CharField(max_length=50, verbose_name='Название на русском')
    name_en = models.CharField(max_length=50, verbose_name='Название на английском')
    name_local = models.CharField(max_length=50, verbose_name='Внутреннее название')
    unece_code = models.CharField(max_length=10, null=True, blank=True, verbose_name='Ephyto code')
    description = models.CharField(max_length=150, verbose_name='Description')
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name_ru

    class Meta:
        verbose_name = 'Единица'
        verbose_name_plural = 'Единицы'
        db_table = 'unit'
        default_permissions = ()


class HSCode(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=250, null=True)
    description = models.TextField(null=True)
    gtk_color_status = models.IntegerField(choices=statuses.HSCodeGTKColorStatus.CHOICES,
                                           default=statuses.HSCodeGTKColorStatus.RED)
    is_lab = models.BooleanField(default=False,
                                 verbose_name='Должен быть проверен лабораторией')
    is_high_risked = models.BooleanField(default=False,
                                 verbose_name='Фитосанитар хавфи юқори бўлган карантин остидаги маҳсулотлар')
    lab_analyzer_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return str(self.code)

    class Meta:
        verbose_name = 'HS Code'
        verbose_name_plural = 'HS Codes'
        db_table = 'hs_code'

        permissions = (
            ('can_change_high_risked_hs_codes', f'Can change high risked {verbose_name}'),
            ('can_change_lab_required_hs_codes', f'Can change lab required {verbose_name}'),
        )


class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='senders')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='receivers')
    title = models.CharField(max_length=512, verbose_name='Заголовок сообщения')
    body = models.TextField(null=True, verbose_name='Тело сообщения')
    read_at = models.DateTimeField(verbose_name='Прочитанное время', blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated время')
    added_at = models.DateTimeField(auto_now_add=True, verbose_name='Добавлено в')

    def __str__(self):
        return str(self.title)

    @property
    def is_read(self):
        return True if self.read_at else False

    @property
    def last_minute_message(self):
        a = datetime.now() - self.updated_at
        return True if a.total_seconds() < 120 else False

    def has_delete_permission(self, user=None):
        return user == self.sender

    class Meta:
        db_table = 'message'
        ordering = ('-id',)


class SMSNotification(models.Model):
    receiver_phone = models.CharField(max_length=12, null=True)
    text = models.CharField(max_length=500, null=True)
    purpose = models.IntegerField(choices=SMSNotificationPurposes.CHOICES)
    status = models.IntegerField(choices=SMSNotificationStatuses.CHOICES, default=SMSNotificationStatuses.WRONG_NUMBER)
    response = models.TextField(null=True, blank=True, verbose_name='Response')
    is_synchronised = models.BooleanField(default=False)
    added_at = models.DateTimeField(auto_now_add=True, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated время')

    @property
    def message_id(self):
        return f'efito_{self.pk}'

    def __str__(self):
        return self.receiver_phone or 'None'

    class Meta:
        db_table = 'sms_notification'


class Organization(models.Model):
    name = models.CharField(max_length=256, verbose_name='Контрагент')
    tin = models.CharField(max_length=15, verbose_name='ИНН', unique=True)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Организация'
        verbose_name_plural = 'Организации'
        db_table = 'organization'


class Balance(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, verbose_name='Сальдо',
                                     related_name='balances')
    region = models.ForeignKey(Region, on_delete=models.CASCADE, verbose_name='региона заявителя')
    service_type = models.IntegerField(choices=InvoiceServices.CHOICES, verbose_name='Service Type')
    amount = models.DecimalField(verbose_name='Сальдо', max_digits=15, decimal_places=2)
    month = models.DateField(verbose_name='Выдано')
    registrar = models.ForeignKey(User, on_delete=models.DO_NOTHING, verbose_name='Бухгалтер')
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False, verbose_name='Добавлено в')

    def __str__(self):
        return self.organization.name

    class Meta:
        verbose_name = 'Сальдо'
        verbose_name_plural = 'Сальдо'
        ordering = ['-month', 'amount']
        db_table = 'balance'


class ContractPayment(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='payments',
                                     verbose_name='Contract')
    region = models.ForeignKey(Region, on_delete=models.CASCADE, verbose_name='региона')
    contract_number = models.CharField(max_length=128, verbose_name='contract_number')
    contract_date = models.DateField(verbose_name='contract_date')
    service_type = models.IntegerField(choices=InvoiceServices.CHOICES, verbose_name='Service Type')
    order_number = models.CharField(max_length=128, verbose_name='Платёжны поручения №')
    payment_amount = models.DecimalField(verbose_name='Сумма платежа', max_digits=15, decimal_places=2)
    payment_date = models.DateField(verbose_name='Дата оплаты')
    accountant = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Бухгалтер')
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False, verbose_name='Добавлено в')

    def __str__(self):
        return str(self.order_number)

    class Meta:
        verbose_name = 'Оплата Contract'
        verbose_name_plural = 'Оплати Contract'
        db_table = 'contract_payment'
        get_latest_by = 'added_at'
        permissions = (
            # region
            ('add_region_contract_payment', f'Can add region {verbose_name}'),
        )


class Refund(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='refunds',
                                     verbose_name='Contract')
    region = models.ForeignKey(Region, on_delete=models.CASCADE, verbose_name='региона')
    application_number = models.CharField(max_length=128, verbose_name='application_number')
    amount = models.DecimalField(verbose_name='Сумма Refund', max_digits=15, decimal_places=2)
    refunded_date = models.DateField(verbose_name='refunded_date')
    service_type = models.IntegerField(choices=InvoiceServices.CHOICES, verbose_name='Service Type')
    accountant = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Бухгалтер')
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False, verbose_name='Добавлено в')

    def __str__(self):
        return str(self.application_number)

    class Meta:
        verbose_name = 'Refund'
        verbose_name_plural = 'Refunds'
        db_table = 'refund'
        get_latest_by = 'added_at'
        permissions = (
            # region
            ('add_region_refund', f'Can add region {verbose_name}'),
        )


class Integration(models.Model):
    organization_name = models.CharField(max_length=128, verbose_name='Organization Name')
    organization_code = models.CharField(max_length=20, verbose_name='Organization Code')
    data_type = models.IntegerField(choices=IntegratedDataType.CHOICES, verbose_name='Service Type')
    url = models.CharField(max_length=512, verbose_name='Sending URL')
    login_url = models.CharField(max_length=512, verbose_name='Login URL', null=True, blank=True)
    username = models.CharField(max_length=20, null=True, blank=True)
    password = models.CharField(max_length=50, null=True, blank=True)
    access_token = models.CharField(max_length=512, null=True, blank=True)
    refresh_token = models.CharField(max_length=512, null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False, verbose_name='Добавлено в')

    def __str__(self):
        return str(self.get_data_type_display()) + ' to ' + self.organization_name

    class Meta:
        verbose_name = 'Integration'
        verbose_name_plural = 'Integrations'
        db_table = 'integration'
        get_latest_by = '-added_at'


class IntegrationData(models.Model):
    integration = models.ForeignKey(Integration, on_delete=models.CASCADE, related_name='data')
    data = JSONField(verbose_name='Sent data')
    content_type = models.IntegerField(choices=ContentTypes.choices, default=ContentTypes.json)
    response = models.TextField(null=True, verbose_name='Response')
    is_synchronised = models.BooleanField(default=False)
    sent_at = models.DateTimeField(verbose_name='Sent at', null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False, verbose_name='Добавлено в')

    def __str__(self):
        return str(self.integration.get_data_type_display()) + ' to ' + self.integration.organization_name

    @property
    def sent_at_in_seconds(self):
        if self.sent_at:
            return self.sent_at.strftime("%d-%m-%Y %H:%M:%S")
        else:
            return self.sent_at

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

    @staticmethod
    def send_integration_data():
        integrating_data = IntegrationData.objects.select_related('integration').filter(is_synchronised=False).order_by('pk')[:100]

        integrated_data = IntegrationData.objects.filter(is_synchronised=True)
        if integrated_data:
            integrated_data.delete()  # clean DB by deleting sent data to GTK

        for data in integrating_data:
            integration = data.integration
            try:
                if data.content_type == ContentTypes.xml:
                    content_type = 'application/xml'
                else:
                    content_type = 'application/json'

                headers = {'Content-Type': content_type}
                if integration.login_url and integration.username and integration.password:
                    if integration.access_token:
                        headers['Authorization'] = f"Bearer {integration.access_token}"
                    else:
                        try:
                            response = requests.post(integration.login_url, headers=headers,
                                                     json={"phone_number": integration.username,
                                                           "otp": integration.password},
                                                     proxies=proxy_config)
                            access_token = json.loads(response.text).get('data').get('token')
                            headers['Authorization'] = f"Bearer {access_token}"
                            integration.access_token = access_token
                            integration.save()
                        except Exception as e:
                            bot.send_message(chat_id=chat_id, text=str(e)[:400])
                            data.response = str(e)[:400]
                            data.save()
                            continue
                data.sent_at = datetime.now()
                data.save()
                response = requests.post(integration.url,
                                         headers=headers,
                                         json=data.data,
                                         proxies=proxy_config,
                                         timeout=120)

                response_time = response.elapsed.total_seconds()
                if response_time > 60:
                    bot.send_message(chat_id=chat_id, text=str(response_time))

                if response.status_code in [200, 300] and response.json()['result'] == 1:
                    data.is_synchronised = True
                else:
                    bot.send_message(chat_id=chat_id, text=str(response.text)[:400])
                data.response = response.text
                data.save()
            except Exception as e:
                bot.send_message(chat_id=chat_id, text=str(e)[:400])
                data.response = str(e)[:400]
                data.save()

    class Meta:
        verbose_name = 'IntegratedData'
        verbose_name_plural = 'IntegratedData'
        db_table = 'integrated_data'
        get_latest_by = '-added_at'


class APIUser(models.Model):
    name = models.CharField(max_length=50)
    token = models.CharField(max_length=150, blank=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False, verbose_name='Добавлено в')

    def generate_token(self):
        return binascii.hexlify(os.urandom(20)).decode()

    def save(self, *args, **kwargs):
        if not self.pk:
            super(APIUser, self).save()
        if not self.token:
            self.token = self.generate_token()

        super(APIUser, self).save()
