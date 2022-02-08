from django.contrib import admin
from invoice.models import Invoice, InvoiceProvidedService, InvoicePayment, InvoiceRefund


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['number', 'given_date', 'service_type', 'payment_amount', 'paid_amount']
    list_filter = ['region']
    search_fields = ['number', 'applicant_tin']

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(InvoicePayment)
class InvoicePaymentAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'number', 'order_number', 'payment_amount', 'payment_date', 'accountant', 'added_at']
    list_filter = ['accountant', 'status']
    search_fields = ['number', 'order_number', 'invoice__number']

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(InvoiceProvidedService)
class InvoiceProvidedServiceAdmin(admin.ModelAdmin):
    list_filter = ['invoice']
    search_fields = ['number']

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(InvoiceRefund)
class InvoiceRefundAdmin(admin.ModelAdmin):

    def has_delete_permission(self, request, obj=None):
        return False
