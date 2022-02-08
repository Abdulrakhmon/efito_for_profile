from django.db import models

from administration.models import Region, Country, User, Unit, District
from administration.statuses import ImpExpLocChoices, DisinfestationType, BioIndicatorType, Languages
from fumigation.managers import IsActiveManager


class FumigationFormula(models.Model):
    name = models.CharField(max_length=128, verbose_name='Наименование', unique=True)
    formula = models.CharField(max_length=128, verbose_name='Формула', unique=True)
    is_active = models.BooleanField(default=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True)

    all_objects = models.Manager()
    objects = IsActiveManager()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Химические формула'
        verbose_name_plural = 'Химические формулы'
        db_table = 'fumigation_formula'


class FumigationInsecticide(models.Model):
    formula = models.ForeignKey(FumigationFormula, on_delete=models.DO_NOTHING, verbose_name='FumigationFormula',
                                related_name='insecticides')
    name = models.CharField(max_length=128, verbose_name='name', unique=True)
    is_active = models.BooleanField(default=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True)

    all_objects = models.Manager()
    objects = IsActiveManager()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Fumigation Insecticide'
        verbose_name_plural = 'Fumigation Insecticides'
        db_table = 'fumigation_insecticide'


class DisinfectedObject(models.Model):
    name = models.CharField(max_length=128, verbose_name='name', unique=True)
    is_active = models.BooleanField(default=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True)

    all_objects = models.Manager()
    objects = IsActiveManager()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Disinfected Object'
        verbose_name_plural = 'Disinfected Objects'
        db_table = 'disinfected_object'


class OrganizationActivityType(models.Model):
    name = models.CharField(max_length=128, verbose_name='name', unique=True)
    is_active = models.BooleanField(default=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True)

    all_objects = models.Manager()
    objects = IsActiveManager()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Organization Activity Type'
        verbose_name_plural = 'Organization Activity Types'
        db_table = 'organization_activity_type'


class FumigationChamber(models.Model):
    region = models.ForeignKey(Region, on_delete=models.DO_NOTHING, verbose_name='Region', related_name='chambers')
    number = models.CharField(max_length=128, verbose_name='name', unique=True)
    is_active = models.BooleanField(default=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True)

    all_objects = models.Manager()
    objects = IsActiveManager()

    def __str__(self):
        return self.number

    class Meta:
        verbose_name = 'Fumigation Chamber'
        verbose_name_plural = 'Fumigation Chamber'
        db_table = 'fumigation_chamber'


class FumigationDeclaration(models.Model):
    name = models.CharField(max_length=128, verbose_name='Name', unique=True)
    description = models.TextField(verbose_name='Description')
    price = models.DecimalField(verbose_name='Price', max_digits=15, decimal_places=2)
    is_active = models.BooleanField(default=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True)

    all_objects = models.Manager()
    objects = IsActiveManager()

    def __str__(self):
        return self.name + ' - ' + str(self.price) + ' сум(' + self.description + ')'

    class Meta:
        verbose_name = 'Fumigation Declaration'
        verbose_name_plural = 'Fumigation Declarations'
        db_table = 'fumigation_declaration'


class InsecticideExchange(models.Model):
    insecticide = models.ForeignKey(FumigationInsecticide, on_delete=models.DO_NOTHING, verbose_name='exchanged insecticide', related_name='exchanges')
    amount = models.DecimalField(verbose_name='amount', max_digits=15, decimal_places=3)
    exchanged_date = models.DateField(verbose_name='Дата выдачи')
    description = models.TextField(verbose_name='Description')
    receiver_region = models.ForeignKey(Region, on_delete=models.DO_NOTHING, verbose_name='Receiver Region', related_name='insecticide_receiver_region')
    sender_region = models.ForeignKey(Region, on_delete=models.DO_NOTHING, verbose_name='Sender Region', related_name='insecticide_sender_region', null=True, blank=True)
    receiver = models.ForeignKey(User, on_delete=models.DO_NOTHING, verbose_name='Receiver', related_name='insecticide_receiver', null=True, blank=True)
    sender = models.ForeignKey(User, on_delete=models.DO_NOTHING, verbose_name='Sender', related_name='insecticide_sender', null=True)
    is_active = models.BooleanField(default=False)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True)

    all_objects = models.Manager()
    objects = IsActiveManager()

    def __str__(self):
        return self.insecticide.name

    class Meta:
        verbose_name = 'Insecticide Exchange'
        verbose_name_plural = 'Insecticide Exchanges'
        db_table = 'insecticide_exchange'


class InsecticidesMonthlyRemainder(models.Model):
    region = models.ForeignKey(Region, on_delete=models.DO_NOTHING, verbose_name='Region')
    fumigation_formula = models.ForeignKey(FumigationFormula, on_delete=models.DO_NOTHING, verbose_name='Fumigation Formula')
    amount = models.DecimalField(verbose_name='Amount', max_digits=15, decimal_places=3)
    end_of_month = models.DateField(verbose_name='Дата выдачи')
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.fumigation_formula.name

    class Meta:
        verbose_name = 'Insecticides Monthly Remainder'
        verbose_name_plural = 'Insecticides Monthly Remainders'
        db_table = 'insecticides_monthly_remainder'


class DisinfectedBuildingType(models.Model):
    name_ru = models.CharField(max_length=256, verbose_name='Name ru')
    name_en = models.CharField(max_length=256, verbose_name='Name en')
    name_local = models.CharField(max_length=256, verbose_name='Name local')
    is_active = models.BooleanField(default=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name='Добавлено в')
    updated_at = models.DateTimeField(auto_now=True)

    all_objects = models.Manager()
    objects = IsActiveManager()

    def __str__(self):
        return self.name_ru

    class Meta:
        verbose_name = 'DisinfectedBuildingType'
        verbose_name_plural = 'DisinfectedBuildingType'
        db_table = 'disinfected_building_type'


class CertificateOfDisinfestation(models.Model):
    region = models.ForeignKey(Region, on_delete=models.CASCADE)
    district = models.ForeignKey(District, on_delete=models.CASCADE)
    number = models.CharField(max_length=20, unique=True, null=True)
    given_date = models.DateField(verbose_name='given_dates')
    language = models.IntegerField(choices=Languages.CHOICES)
    type = models.IntegerField(choices=ImpExpLocChoices.CHOICES)
    organization_name = models.CharField(verbose_name='Организация', max_length=512, null=True)
    organization_tin = models.CharField(verbose_name='ИНН заявителя', max_length=15, null=True)
    organization_activity_type = models.ForeignKey(OrganizationActivityType, on_delete=models.CASCADE, null=True)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, null=True, blank=True)
    insecticide = models.ForeignKey(FumigationInsecticide, on_delete=models.CASCADE, null=True, blank=True)
    insecticide_dosage = models.DecimalField(max_digits=15, decimal_places=3, null=True, blank=True)
    insecticide_unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='insecticide_unit', null=True, blank=True)
    declaration_price = models.DecimalField(max_digits=15, decimal_places=2)
    total_price = models.DecimalField(max_digits=15, decimal_places=2)
    fumigator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fumigator')
    inspector = models.ForeignKey(User, on_delete=models.CASCADE, related_name='inspector')
    customer = models.CharField(verbose_name='Customer', max_length=512, null=True)
    disinfected_building_type = models.ForeignKey(DisinfectedBuildingType, on_delete=models.CASCADE)
    fumigation_chamber = models.ForeignKey(FumigationChamber, on_delete=models.CASCADE, null=True, blank=True, related_name='certificates_of_disinfestation')
    disinfected_building_info = models.CharField(max_length=512, null=True, blank=True)
    disinfected_building_volume = models.DecimalField(max_digits=15, decimal_places=3)
    disinfected_building_unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='disinfected_building_unit')
    expended_insecticide_amount = models.DecimalField(max_digits=15, decimal_places=3, null=True)
    disinfected_product = models.CharField(max_length=512, null=True, blank=True)
    disinfected_product_amount = models.DecimalField(max_digits=15, decimal_places=3, null=True, blank=True)
    disinfected_product_unit = models.ForeignKey(Unit, on_delete=models.CASCADE, null=True, blank=True)
    disinfestation_type = models.IntegerField(choices=DisinfestationType.CHOICES, default=DisinfestationType.FUMIGATION)
    temperature = models.CharField(max_length=120, null=True, blank=True)
    beginning_of_disinfection = models.DateTimeField(null=True, blank=True)
    ending_of_disinfection = models.DateTimeField(null=True, blank=True)
    degassing_time = models.CharField(max_length=120, null=True, blank=True)
    beginning_of_cycle = models.DateTimeField(null=True, blank=True)
    beginning_of_heat_treatment = models.DateTimeField(null=True, blank=True)
    ending_of_heat_treatment = models.DateTimeField(null=True, blank=True)
    ending_of_cycle = models.DateTimeField(null=True, blank=True)
    temperature_in_beginning_of_cycle = models.CharField(max_length=5, null=True, blank=True)
    temperature_in_beginning_of_heat_treatment = models.CharField(max_length=5, null=True, blank=True)
    wetness_in_beginning_of_cycle = models.CharField(max_length=5, null=True, blank=True)
    wetness_in_beginning_of_heat_treatment = models.CharField(max_length=5, null=True, blank=True)
    is_duration_in_established_standard = models.BooleanField(null=True, blank=True)
    is_temperature_in_established_standard = models.BooleanField(null=True, blank=True)
    bio_indicator = models.IntegerField(choices=BioIndicatorType.CHOICES, default=BioIndicatorType.BARNPEST)
    disinfection_result = models.CharField(max_length=120, null=True, blank=True)
    disinfected_object = models.ForeignKey(DisinfectedObject, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    added_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    all_objects = models.Manager()
    objects = IsActiveManager()

    def __str__(self):
        return self.number

    # @property
    # def expended_insecticide_amount(self):
    #     return self.insecticide_dosage * self.disinfected_building_volume

    @property
    def disinfected_building_type_name(self):
        if self.language == 2:
            return str(self.disinfected_building_type.name)
        else:
            return str(self.disinfected_building_type.name)

    @property
    def fumigator_fullname(self):
        fumigator_name = ''
        if self.fumigator:
            if self.language == Languages.ENGLISH:
                fumigator_name = self.fumigator.name_en
            else:
                fumigator_name = self.fumigator.name_ru
            fumigator_name = fumigator_name.split()
            fumigator_name = str(fumigator_name[0] + ' ' + fumigator_name[1][0])
        return fumigator_name

    @property
    def inspector_fullname(self):
        inspector_name = ''
        if self.inspector:
            if self.language == Languages.ENGLISH:
                inspector_name = self.inspector.name_en
            else:
                inspector_name = self.inspector.name_ru
            inspector_name = inspector_name.split()
            inspector_name = str(inspector_name[0] + ' ' + inspector_name[1][0])
        return inspector_name

    @property
    def inspection(self):
        if self.region:
            if self.language == Languages.ENGLISH:
                return self.region.name_en
            else:
                return self.region.name_ru
        return ''

    class Meta:
        ordering = ["-pk"]
        verbose_name = 'Certificates Of Disinfestation'
        verbose_name_plural = 'Certificate Of Disinfestation'
        db_table = 'certificate_of_disinfestation'

        permissions = (
            # republic
            ('list_republic_certificate_of_disinfestation', f'Can list republic {verbose_name}'),

            # region
            ('list_region_certificate_of_disinfestation', f'Can list region {verbose_name}'),

            # fumigator
            ('list_fumigator_certificate_of_disinfestation', f'Can list fumigator {verbose_name}'),
            ('add_certificate_of_disinfestation', f'Can add fumigator {verbose_name}'),
            ('edit_certificate_of_disinfestation', f'Can edit fumigator {verbose_name}'),
            ('delete_certificate_of_disinfestation', f'Can delete fumigator {verbose_name}'),
        )