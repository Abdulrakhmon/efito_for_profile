from django.contrib import admin

from ppp.models import PPPRegistrationProtocolScope, PPPRegistrationProtocol, Biocide


@admin.register(Biocide)
class BiocideAdmin(admin.ModelAdmin):
    list_display = ['name_ru', 'name_uz', 'code', 'added_at', 'updated_at']
    search_fields = ['name_uz', 'name_ru', 'code']
    list_filter = ['is_active']

    def has_delete_permission(self, request, obj=None):
        return False


class PPPRegistrationProtocolScopeInline(admin.TabularInline):
    extra = 0
    model = PPPRegistrationProtocolScope


# ADMINS
@admin.register(PPPRegistrationProtocol)
class PPPRegistrationProtocolAdmin(admin.ModelAdmin):
    inlines = [PPPRegistrationProtocolScopeInline]
    list_display = ['number', 'applicant_name', 'added_at', 'updated_at']
    search_fields = ['number', 'applicant_name']
    list_filter = ['biocide', 'country']

    def has_delete_permission(self, request, obj=None):
        return False
