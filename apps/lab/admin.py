from django.contrib import admin
from exim.models import TBOTD
from lab.models import ImportShortcut, ImportProtocol, ImportShortcutProduct, ImportProtocolConclusion, \
    LabChemicalReactive, LabDisposable, UsedChemicalReactive, UsedDisposable, LabTestMethod


# class TBOTDInline(admin.TabularInline):
#     extra = 0
#     model = TBOTD
#
#     def has_add_permission(self, request, obj=None):
#         return False
#
#     def has_change_permission(self, request, obj=None):
#         return False
#
#
class ImportShortcutProductInline(admin.TabularInline):
    raw_id_fields = ('import_shortcut', 'shipment_product')
    extra = 0
    model = ImportShortcutProduct


class ImportProtocolConclusionInline(admin.TabularInline):
    extra = 0
    model = ImportProtocolConclusion


@admin.register(ImportShortcut)
class ImportShortcutAdmin(admin.ModelAdmin):
    inlines = ImportShortcutProductInline,
    raw_id_fields = ('ikr',)
    list_display = ['number', 'added_at']
    search_fields = ['number']


@admin.register(ImportShortcutProduct)
class ImportShortcutProductAdmin(admin.ModelAdmin):
    raw_id_fields = ('import_shortcut', 'shipment_product',)
    list_display = ['name', 'added_at']
    list_filter = ['import_shortcut']
    search_fields = ['name']


@admin.register(ImportProtocol)
class ImportProtocolAdmin(admin.ModelAdmin):
    inlines = ImportProtocolConclusionInline,
    list_display = ['number', 'given_date', 'shortcut_number']
    search_fields = ['number']

    # def has_delete_permission(self, request, obj=None):
    #     return False


@admin.register(LabChemicalReactive)
class LabChemicalReactiveAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'unit']
    search_fields = ['name']


@admin.register(LabDisposable)
class LabDisposableAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'unit']
    search_fields = ['name']


@admin.register(UsedChemicalReactive)
class UsedChemicalReactiveAdmin(admin.ModelAdmin):
    raw_id_fields = ('import_protocol_conclusion', 'lab_chemical_reactive',)
    list_display = ['amount']
    search_fields = ['amount']


@admin.register(UsedDisposable)
class UsedDisposableAdmin(admin.ModelAdmin):
    list_display = ['amount']
    search_fields = ['amount']


@admin.register(LabTestMethod)
class LabTestMethodAdmin(admin.ModelAdmin):
    list_display = ['name', 'expertise_type']
    search_fields = ['name']