import datetime

from django.db import models
from django.urls import reverse

from administration.models import Country, User
from ppp.managers import IsActiveManager, IsApprovedManager
from ppp.statuses import PPPProtocolStatuses


class Biocide(models.Model):
    name_uz = models.CharField(max_length=128, verbose_name='Наименование', unique=True)
    name_ru = models.CharField(max_length=128, verbose_name='Наименование', unique=True)
    code = models.CharField(max_length=2, verbose_name='Формула', unique=True)
    counter = models.IntegerField(default=0)
    yearly_counter = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    added_at = models.DateTimeField(auto_now_add=True, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True)

    all_objects = models.Manager()
    objects = IsActiveManager()

    def __str__(self):
        return self.name_ru

    class Meta:
        verbose_name = 'Biocide'
        verbose_name_plural = 'Biocides'
        db_table = 'biocide'


class PPPRegistrationProtocol(models.Model):
    serial_number = models.CharField(max_length=1)
    order_number = models.CharField(unique=True, max_length=6, null=True, blank=True)
    number = models.CharField(unique=True, max_length=7, null=True, blank=True)
    given_date = models.DateField(verbose_name='Выдано', null=True, blank=True)
    expire_date = models.DateField(verbose_name='Cроком до')
    protocol_number = models.CharField(max_length=5, null=True, blank=True)
    protocol_given_date = models.DateField(null=True, blank=True)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='ppp_registration_protocols')
    applicant_tin = models.CharField(verbose_name='ИНН', max_length=15, null=True, blank=True)
    applicant_name = models.CharField(max_length=150)
    applicant_phone = models.CharField(max_length=9)
    biocide = models.ForeignKey(Biocide, on_delete=models.CASCADE, related_name='ppp_registration_protocols', verbose_name='препарат шакли')
    biocide_registered_number = models.CharField(max_length=10, verbose_name='Препаратни рўйхатга олинганлик рақами', null=True, blank=True)
    biocide_registered_date = models.DateField(verbose_name='Препаратни рўйхатга олинганлик санаси', null=True, blank=True)
    biocide_trade_name = models.CharField(max_length=150, verbose_name='Савдо номи')
    concentration = models.CharField(max_length=256)
    irritant_substance = models.CharField(max_length=256, verbose_name='таъсир этувчи модда')
    status = models.IntegerField(choices=PPPProtocolStatuses.CHOICES, default=PPPProtocolStatuses.SAVED)
    registerer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='registers_ppprps')
    approved_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='approver_ppprps')
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    all_objects = models.Manager()
    objects = IsApprovedManager()

    def __str__(self):
        return self.number if self.number else self.serial_number

    def get_absolute_url(self):
        return reverse('exim:view_ikr', kwargs={'pk': self.id})

    @property
    def is_valid(self):
        return self.deadline >= datetime.date.today()

    class Meta:
        verbose_name = 'ЎСИМЛИКЛАРНИ ҲИМОЯ ҚИЛИШНИНГ КИМЁВИЙ ВА БИОЛОГИК ВОСИТАЛАРИ ҲАМДА МИНЕРАЛ ВА МИКРОБИОЛОГИК ' \
                       'ЎҒИТЛАРНИ РЎЙХАТГА ОЛИНГАНЛИК ТЎҒРИСИДА ГУВОҲНОМА'
        verbose_name_plural = 'ЎСИМЛИКЛАРНИ ҲИМОЯ ҚИЛИШНИНГ КИМЁВИЙ ВА БИОЛОГИК ВОСИТАЛАРИ ҲАМДА МИНЕРАЛ ВА ' \
                              'МИКРОБИОЛОГИК ЎҒИТЛАРНИ РЎЙХАТГА ОЛИНГАНЛИК ТЎҒРИСИДА ГУВОҲНОМАЛАР'
        db_table = 'ppp_registration_protocol'
        ordering = ['-updated_at']
        default_permissions = ()

        permissions = (
            ('list_ppp_registration_protocols', f'Can list {verbose_name}'),
            ('add_ppp_registration_protocols', f'Can add {verbose_name}'),
            ('send_to_approve_ppp_registration_protocols', f'Can send to approve {verbose_name}'),
            ('approve_ppp_registration_protocols', f'Can approve {verbose_name}'),
        )


UNIT_CHOICES = (
    (1, 'л/га'),
    (2, 'кг/га'),
    (3, 'л/т'),
    (4, 'кг/т')
)


class PPPRegistrationProtocolScope(models.Model):
    ppp_registration_protocol = models.ForeignKey(PPPRegistrationProtocol, on_delete=models.CASCADE,
                                                  related_name='scopes')
    plant_type_uz = models.CharField(max_length=100, verbose_name='Препаратдан фойдаланиладиган экин тури')
    plant_type_ru = models.CharField(max_length=100, verbose_name='Препаратдан фойдаланиладиган экин тури')
    harmful_organisms_uz = models.CharField(max_length=256, verbose_name='Қайси зарарли организмга қарши ишлатилади')
    harmful_organisms_ru = models.CharField(max_length=256, verbose_name='Қайси зарарли организмга қарши ишлатилади')
    amount = models.CharField(max_length=10)
    unit = models.PositiveSmallIntegerField(choices=UNIT_CHOICES)
    scope_uz = models.CharField(max_length=512, verbose_name='Ишлатиш муддати, усули ва тавсия этилган чекловлар')
    scope_ru = models.CharField(max_length=512, verbose_name='Ишлатиш муддати, усули ва тавсия этилган чекловлар')
    day = models.CharField(max_length=20, verbose_name='Ҳосилни йиғишга қанча қолганда ишлов тугалланади, кун', null=True, blank=True)
    time = models.PositiveSmallIntegerField(verbose_name='Бир мавсумда кўпи билан неча марта ишлатилади', null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.plant_type_uz

    class Meta:
        verbose_name = 'Қўллаш доираси'
        verbose_name_plural = 'Қўллаш доиралари'
        db_table = 'ppp_registration_protocol_scope'
