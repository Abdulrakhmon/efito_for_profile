from django.contrib import admin
from exim.models import IKR, IKRProduct, IKRShipment, IKRShipmentProduct, AKD, TBOTD, Transit, WrongIKR, IKRExtension, \
    TBOTDRejectionInfo, WrongAKD, OldAKD, JsonIKR, GivenBlanks, ExportFSSProduct, WrongExportFSS, JsonExportFSS, \
    SURSystem, LocalFSS, LocalFSSProduct, Pest, PestDistributedCountry, ExportFSS, PestHSCode, PestImage, \
    SURSystemHSCode, ImportFSS, ImportFSSProduct, AKDApplication, ExportFSSApplication, AKDApplicationStatusStep, \
    ExportFSSApplicationStatusStep, IKRApplication, IKRApplicationStatusStep, IKRRenewalApplication, \
    IKRRenewalApplicationStatusStep, WrongApplication, TBOTDExtraInfo, TemporarilyStoppedShipment, \
    TemporarilyStoppedShipmentProduct, LocalFSSApplication, LocalFSSApplicationStatusStep, LocalFSSImage


# admin.site.disable_action('delete_selected')
# # INLINE ADMINS
class IKRProductInline(admin.TabularInline):
    extra = 0
    model = IKRProduct


class IKRShipmentInline(admin.TabularInline):
    extra = 0
    model = IKRShipment


class IKRShipmentProductInline(admin.TabularInline):
    extra = 0
    model = IKRShipmentProduct


class IKRExtensionInline(admin.TabularInline):
    extra = 0
    model = IKRExtension


class JsonIKRInline(admin.TabularInline):
    model = JsonIKR
    readonly_fields = ['json', 'added_at', 'updated_at']


class TBOTDExtraInfoInline(admin.TabularInline):
    extra = 0
    model = TBOTDExtraInfo


class TBOTDRejectionInfoInline(admin.TabularInline):
    extra = 0
    model = TBOTDRejectionInfo


class ExportFSSProductInline(admin.TabularInline):
    extra = 0
    model = ExportFSSProduct


class ImportFSSProductInline(admin.TabularInline):
    extra = 0
    model = ImportFSSProduct


class LocalFSSProductInline(admin.TabularInline):
    extra = 0
    model = LocalFSSProduct


class PestDistributedCountryInline(admin.TabularInline):
    extra = 0
    model = PestDistributedCountry


class PestHSCodeInline(admin.TabularInline):
    extra = 0
    model = PestHSCode


class PestImageInline(admin.TabularInline):
    extra = 0
    model = PestImage
    readonly_fields = ('image_tag',)


class SURSystemHSCodeInline(admin.TabularInline):
    extra = 0
    model = SURSystemHSCode


class JsonExportFSSInline(admin.TabularInline):
    model = JsonExportFSS
    readonly_fields = ['json', 'added_at', 'updated_at']


# ADMINS
@admin.register(IKR)
class IKRAdmin(admin.ModelAdmin):
    raw_id_fields = ('application', 'sms_notification')
    inlines = [IKRProductInline, IKRExtensionInline, JsonIKRInline]
    list_display = ['number', 'request_number', 'added_at', 'updated_at']
    sortable_by = ['added_at', 'given_date', 'updated_at']
    search_fields = ['number', 'request_number', 'importer_name', 'importer_representative_name', 'importer_address',
                     'crpp_number']
    list_filter = ['language', 'importer_type', 'transport_method', 'point', 'is_approved', 'is_transit', 'owner', 'considered_by']
    readonly_fields = ['added_at']

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(JsonIKR)
class JsonIKRAdmin(admin.ModelAdmin):
    list_display = ['ikr', 'added_at', 'updated_at']
    list_filter = ['added_at', 'updated_at']
    readonly_fields = ['json', 'added_at', 'updated_at']
    sortable_by = ['added_at', 'updated_at']
    search_fields = ['json']


@admin.register(IKRShipment)
class IKRShipmentAdmin(admin.ModelAdmin):
    # inlines = [IKRShipmentProductInline]
    raw_id_fields = ('ikr', 'akd_application', 'registerer_point', 'inspector', 'sms_notification',)
    list_display = ['info', 'is_notified', 'added_at', 'updated_at', 'sent_at']
    search_fields = ['info']
    list_filter = ['status']

    # def has_delete_permission(self, request, obj=None):
    #     return False


@admin.register(IKRShipmentProduct)
class IKRShipmentProductAdmin(admin.ModelAdmin):
    raw_id_fields = ('ikr_shipment', 'ikr_product',)
    search_fields = ['quantity']
    list_display = ['name', 'quantity', 'is_damaged', 'added_at', 'updated_at']


@admin.register(TBOTD)
class TBOTDAdmin(admin.ModelAdmin):
    raw_id_fields = ('ikr_shipment', 'lab_shortcut',)
    list_display = ['number', 'added_at', 'added_at']
    search_fields = ['number']
    inlines = TBOTDRejectionInfoInline, TBOTDExtraInfoInline,

    # def has_delete_permission(self, request, obj=None):
    #     return False


@admin.register(AKD)
class AKDAdmin(admin.ModelAdmin):
    raw_id_fields = ('tbotd', 'sms_notification',)
    list_filter = ['is_synchronised', 'inspector']
    search_fields = ['number']
    list_display = ['number', 'is_synchronised', 'is_active', 'added_at', 'updated_at']


@admin.register(ExportFSS)
class ExportFSSAdmin(admin.ModelAdmin):
    raw_id_fields = ('application', 'sms_notification')
    list_display = ['number', 'exporter_name', 'exporter_country', 'given_date', 'added_at', 'updated_at']
    list_filter = ['added_at', 'synchronisation_status', 'is_synchronised', 'updated_at', 'language', 'transport_method',
                   'inspector', 'exporter_country', 'exporter_region', 'importer_country']
    search_fields = ['number', 'order_number', 'local_fss_number', 'request_number', 'registered_number', 'exporter_name', 'importer_name']
    inlines = ExportFSSProductInline, JsonExportFSSInline

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ImportFSS)
class ImportFSSAdmin(admin.ModelAdmin):
    list_display = ['number', 'exporter_name', 'exporter_country', 'given_date', 'added_at']
    list_filter = ['added_at', 'updated_at', 'transport_method',
                   'exporter_country',  'importer_country']
    search_fields = ['number', 'exporter_name', 'importer_name']
    inlines = ImportFSSProductInline,


class LocalFSSImageInline(admin.TabularInline):
    extra = 0
    model = LocalFSSImage


@admin.register(LocalFSS)
class LocalFSSAdmin(admin.ModelAdmin):
    list_display = ['number', 'given_date', 'applicant_name', 'sender_region', 'field_id', 'added_at', 'updated_at']
    list_filter = ['sender_region', 'inspector']
    search_fields = ['number']
    inlines = [LocalFSSProductInline, LocalFSSImageInline]


@admin.register(SURSystem)
class SURSystemAdmin(admin.ModelAdmin):
    list_display = ['country', 'farm', 'is_allowed']
    list_filter = ['registered_date', 'country']
    search_fields = ('country', 'farm')
    inlines = [SURSystemHSCodeInline]


@admin.register(Pest)
class PestAdmin(admin.ModelAdmin):
    list_display = ['name_ru']
    inlines = [PestDistributedCountryInline, PestHSCodeInline, PestImageInline]


@admin.register(WrongIKR)
class WrongIKRAdmin(admin.ModelAdmin):
    search_fields = ['ikr']
    list_display = ['id', 'action', 'added_at', 'updated_at']
    readonly_fields = ['ikr', 'exception_details', 'action', 'added_at', 'updated_at']
    list_filter = ['action', 'added_at', 'updated_at']
    sortable_by = ['added_at', 'updated_at']


@admin.register(WrongAKD)
class WrongAKDAdmin(admin.ModelAdmin):
    search_fields = ['tried_json', 'description']
    list_display = ['id', 'trials_count', 'added_at']
    readonly_fields = ['tried_json', 'description', 'trials_count', 'added_at']
    list_filter = ['added_at', 'updated_at', 'error_type']
    sortable_by = ['trials_count', 'added_at', 'updated_at']


@admin.register(WrongExportFSS)
class WrongExportFSSAdmin(admin.ModelAdmin):
    search_fields = ['json']
    list_display = ['id', 'action', 'added_at', 'updated_at']
    readonly_fields = ['json', 'exception_details', 'action', 'added_at', 'updated_at']
    list_filter = ['action', 'added_at', 'updated_at']
    sortable_by = ['added_at', 'updated_at']


@admin.register(OldAKD)
class OldAKDAdmin(admin.ModelAdmin):
    list_display = ['sw_id', 'added_at', 'updated_at']
    list_filter = ['added_at', 'updated_at']
    readonly_fields = ['added_at', 'updated_at']
    sortable_by = ['added_at', 'updated_at']
    search_fields = ['json']

    def has_delete_permission(self, request, obj=None):
        return False


class AKDApplicationStatusStepInline(admin.TabularInline):
    extra = 0
    model = AKDApplicationStatusStep


@admin.register(AKDApplication)
class AKDApplicationAdmin(admin.ModelAdmin):
    search_fields = ['request_number', 'importer_tin', 'transport_number']
    list_filter = ['is_active']
    list_display = ['request_number', 'transport_number', 'ikr', 'received_at_in_seconds', 'added_at_in_seconds',
                    'updated_at_in_seconds', 'is_active']
    inlines = [AKDApplicationStatusStepInline]

    def has_delete_permission(self, request, obj=None):
        return False


class IKRApplicationStatusStepInline(admin.TabularInline):
    extra = 0
    model = IKRApplicationStatusStep


@admin.register(IKRApplication)
class IKRApplicationAdmin(admin.ModelAdmin):
    search_fields = ['request_number']
    list_filter = ['is_active', 'status']
    list_display = ['request_number', 'received_at_in_seconds', 'added_at_in_seconds', 'updated_at_in_seconds', 'is_active']
    inlines = [IKRApplicationStatusStepInline]

    def has_delete_permission(self, request, obj=None):
        return False


class IKRRenewalApplicationStatusStepInline(admin.TabularInline):
    extra = 0
    model = IKRRenewalApplicationStatusStep


@admin.register(IKRRenewalApplication)
class IKRApplicationAdmin(admin.ModelAdmin):
    search_fields = ['request_number']
    list_filter = ['is_active']
    list_display = ['request_number', 'received_at_in_seconds', 'added_at_in_seconds', 'updated_at_in_seconds', 'is_active']
    inlines = [IKRRenewalApplicationStatusStepInline]

    def has_delete_permission(self, request, obj=None):
        return False


class ExportFSSApplicationStatusStepInline(admin.TabularInline):
    extra = 0
    model = ExportFSSApplicationStatusStep


@admin.register(ExportFSSApplication)
class ExportFSSApplicationAdmin(admin.ModelAdmin):
    search_fields = ['request_number', 'exporter_tin', 'transport_number']
    list_filter = ['is_active']
    list_display = ['request_number', 'transport_number', 'exporter_tin', 'received_at_in_seconds',
                    'added_at_in_seconds', 'updated_at_in_seconds', 'is_active']
    inlines = [ExportFSSApplicationStatusStepInline]

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(WrongApplication)
class WrongApplicationAdmin(admin.ModelAdmin):
    search_fields = ['json']
    list_display = ['pk', 'exception_details', 'updated_at']


@admin.register(GivenBlanks)
class GivenBlanksAdmin(admin.ModelAdmin):
    search_fields = ['first_blank_number']
    list_display = ['first_blank_number', 'added_at']

    def has_delete_permission(self, request, obj=None):
        return False


# @admin.register(Transit)
# class TransitAdmin(admin.ModelAdmin):
#     list_display = ['ikr_shipment', 'inspector','', 'added_at']

@admin.register(IKRProduct)
class IKRProductsAdmin(admin.ModelAdmin):
    raw_id_fields = ('ikr',)
    search_fields = ['name']
    list_display = ['name', 'quantity', 'ikr_number', 'is_netto', 'added_at', 'updated_at']

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(Transit)
admin.site.register(TemporarilyStoppedShipment)
admin.site.register(TemporarilyStoppedShipmentProduct)


class LocalFSSApplicationStatusStepInline(admin.TabularInline):
    extra = 0
    model = LocalFSSApplicationStatusStep


@admin.register(LocalFSSApplication)
class LocalFSSApplicationAdmin(admin.ModelAdmin):
    list_display = ['request_number', 'request_date', 'applicant_name', 'sender_region', 'field_id', 'added_at', 'updated_at']
    list_filter = ['sender_region']
    search_fields = ['request_number']
    inlines = [LocalFSSApplicationStatusStepInline]
