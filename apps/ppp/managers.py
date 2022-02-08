from django.db.models import Manager

from ppp.statuses import PPPProtocolStatuses


class IsActiveManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class IsApprovedManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status=PPPProtocolStatuses.APPROVED)