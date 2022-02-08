from django.contrib import admin

# ADMINS
from fumigation.models import FumigationFormula, FumigationInsecticide, DisinfectedObject, FumigationChamber, \
    FumigationDeclaration, CertificateOfDisinfestation, DisinfectedBuildingType, InsecticidesMonthlyRemainder, \
    InsecticideExchange, OrganizationActivityType


@admin.register(FumigationFormula)
class FumigationFormulaAdmin(admin.ModelAdmin):
    list_filter = ['is_active']

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(FumigationInsecticide)
class FumigationInsecticideAdmin(admin.ModelAdmin):
    search_fields = ['name']
    list_filter = ['is_active']
    list_display = ['name', 'formula', 'is_active']

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DisinfectedBuildingType)
class DisinfectedBuildingTypeAdmin(admin.ModelAdmin):
    search_fields = ['name_ru']
    list_filter = ['is_active']
    list_display = ['name_ru', 'is_active']

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DisinfectedObject)
class DisinfectedObjectAdmin(admin.ModelAdmin):
    search_fields = ['name']
    list_filter = ['is_active']
    list_display = ['name', 'is_active']

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(OrganizationActivityType)
class OrganizationActivityTypeAdmin(admin.ModelAdmin):
    search_fields = ['name']
    list_filter = ['is_active']
    list_display = ['name', 'is_active']

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(FumigationChamber)
class FumigationChamberAdmin(admin.ModelAdmin):
    search_fields = ['number']
    list_filter = ['is_active']
    list_display = ['number', 'is_active']

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(FumigationDeclaration)
class FumigationDeclarationAdmin(admin.ModelAdmin):
    search_fields = ['name']
    list_filter = ['is_active']
    list_display = ['name', 'description', 'price', 'is_active']

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(InsecticidesMonthlyRemainder)
class InsecticidesMonthlyRemainderAdmin(admin.ModelAdmin):
    list_filter = ['fumigation_formula', 'region']
    list_display = ['region', 'fumigation_formula', 'amount', 'end_of_month']


@admin.register(InsecticideExchange)
class InsecticideExchangeAdmin(admin.ModelAdmin):
    list_filter = ['insecticide', 'receiver_region', 'sender_region', 'is_active']
    list_display = ['receiver_region', 'insecticide', 'amount', 'sender_region', 'exchanged_date']

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CertificateOfDisinfestation)
class CertificateOfDisinfestationAdmin(admin.ModelAdmin):
    search_fields = ['number']
    list_filter = ['is_active', 'region', 'inspector', 'fumigator', 'fumigation_chamber']
    list_display = ['number', 'given_date', 'region', 'fumigator', 'added_at', 'updated_at']

    def has_delete_permission(self, request, obj=None):
        return False