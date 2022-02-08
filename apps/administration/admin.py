from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Permission
from administration.models import Country, Region, Unit, User, Point, HSCode, Message, District, SMSNotification, \
    Organization, Balance, ContractPayment, Refund, Integration, IntegrationData, APIUser, UserRegistrationRequest, \
    UserPoints

admin.site.register(Region)

@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ['name_ru', 'code']
    search_fields = ['code', 'name_ru', 'name_en', 'name_local', 'gtk_code']

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ['name_ru', 'name_en', 'code']
    search_fields = ['code', 'name_ru', 'name_en']

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(HSCode)
class HSCodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'is_lab', 'is_high_risked', 'added_at', 'updated_at']
    list_filter = ['is_lab', 'is_high_risked', 'gtk_color_status']
    search_fields = ['code', 'name']

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ['name_ru', 'name_en', 'code']
    search_fields = ['name_ru', 'name_en', 'code']
    list_filter = ['region']


@admin.register(Point)
class PointAdmin(admin.ModelAdmin):
    list_display = ['name_ru', 'name_en', 'code']
    search_fields = ['name_ru', 'name_en', 'code']
    list_filter = ['region']

    def has_delete_permission(self, request, obj=None):
        return False


class UserRegistrationRequestInline(admin.TabularInline):
    model = UserRegistrationRequest
    fk_name = "user"


class UserPointsInline(admin.TabularInline):
    model = UserPoints
    fk_name = "user"


class CustomUserAdmin(UserAdmin):
    change_user_password_template = None
    model = User
    list_display = ['name_ru', 'name_en', 'name_local', 'phone', 'username', 'point']
    list_filter = ['status', 'point']
    search_fields = ['username', 'name_ru']
    filter_vertical = []
    filter_horizontal = []
    fieldsets = [
        [
            "Authentication",
            {
                'fields': [
                    'username',
                    'password',
                ]
            }
        ],
        [
            "Details",
            {
                'fields': [
                    'name_ru',
                    'name_en',
                    'name_local',
                    'tin',
                    'phone',
                    'point',
                ]
            }
        ],
        [
            'Authorization',
            {
                'fields': [
                    'groups',
                    'user_permissions',
                    'is_esi_required',
                    'status',
                    'is_staff',
                    'is_superuser',
                ]
            }
        ],
    ]
    add_fieldsets = [
        [
            "Authentication",
            {
                'fields': [
                    'username',
                    'password1',
                    'password2',
                ],
            }
        ],
        [
            "Details",
            {
                'classes': ['wide'],
                'fields': [
                    'name_ru',
                    'name_en',
                    'name_local',
                    'tin',
                    'phone',
                    'point',
                ],
            }
        ],
        [
            'Authorization',
            {
                'fields': [
                    'groups',
                    'user_permissions',
                    'status',
                ]
            }
        ]
    ]
    inlines = [UserRegistrationRequestInline, UserPointsInline]

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(User, CustomUserAdmin)
admin.site.register(Permission)
admin.site.register(APIUser)


# admin.site.register(Message)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['title', 'added_at', 'updated_at']
    search_fields = ['title']


@admin.register(SMSNotification)
class SMSNotificationAdmin(admin.ModelAdmin):
    search_fields = ('receiver_phone', 'text')
    list_filter = ('purpose', 'status', 'added_at', 'updated_at')
    list_display = ('receiver_phone', 'purpose', 'status', 'added_at', 'updated_at')


class BalanceInline(admin.TabularInline):
    extra = 0
    model = Balance


class ContractPaymentInline(admin.TabularInline):
    extra = 0
    model = ContractPayment


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    search_fields = ['name', 'tin']
    inlines = [BalanceInline, ContractPaymentInline]


@admin.register(Balance)
class BalanceAdmin(admin.ModelAdmin):
    search_fields = ['amount']
    list_display = ('organization', 'amount', 'region', 'service_type', 'added_at', 'updated_at')
    list_filter = ('region', 'service_type', 'added_at', 'updated_at')


@admin.register(ContractPayment)
class ContractPaymentAdmin(admin.ModelAdmin):
    search_fields = ['order_number', 'payment_amount']


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    search_fields = ['application_number', 'amount_in_applicant']


@admin.register(Integration)
class IntegrationAdmin(admin.ModelAdmin):
    search_fields = ('organization_name', 'organization_nickname', '')
    list_filter = ('data_type', 'url')


@admin.register(IntegrationData)
class IntegrationDataAdmin(admin.ModelAdmin):
    search_fields = ('data',)
    list_filter = ('is_synchronised', 'integration')
    list_display = ('integration', 'is_synchronised', 'added_at_in_seconds', 'sent_at_in_seconds', 'updated_at_in_seconds')
