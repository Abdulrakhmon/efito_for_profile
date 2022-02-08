from django.db.models import Manager

from core import settings
from invoice.statuses import InvoicePaymentStatuses


class ActiveInvoicesManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(given_date__gte=settings.FIRST_DATE_OF_CURRENT_YEAR)


class InvoicePaymentManager(Manager):
    def confirmed(self):
        return self.get_queryset().filter(status=InvoicePaymentStatuses.confirmed)

    def not_confirmed(self):
        return self.get_queryset().filter(status=InvoicePaymentStatuses.not_confirmed)

    def rejected(self):
        return self.get_queryset().filter(status=InvoicePaymentStatuses.rejected)

    def cancelled(self):
        return self.get_queryset().filter(status=InvoicePaymentStatuses.cancelled)