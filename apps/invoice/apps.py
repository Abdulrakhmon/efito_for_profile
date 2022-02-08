from django.apps import AppConfig


class InvoiceConfig(AppConfig):
    name = 'invoice'

    # def ready(self):
    #     import apps.invoice.api.munis_webservice.munis_signals
