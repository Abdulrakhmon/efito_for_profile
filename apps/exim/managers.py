import datetime
from django.db.models import Manager, Q
from administration.statuses import IKRShipmentStatuses


class IKRShipmentManager(Manager):
    def pending(self):
        return self.get_queryset().filter(status__in=[IKRShipmentStatuses.COMING, IKRShipmentStatuses.ARRIVED,
                                                      IKRShipmentStatuses.LATE], tbotd__isnull=True)

    def approved(self):
        return self.get_queryset().filter(status=IKRShipmentStatuses.APPROVED, akd__isnull=False)


class IKRManager(Manager):
    def valids(self):
        today = datetime.date.today()
        return self.get_queryset().filter(Q(expire_date__gte=today) | Q(extensions__expire_date__gte=today))


class IKRShipmentProductManager(Manager):
    def damageds(self):
        return self.get_queryset().filter(is_damaged=True)


class IsApprovedManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_approved=True, is_active=True)


class IsUnapprovedManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_approved=False)


class IsIKRUnapprovedManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(Q(is_approved=False) | Q(is_synchronised=False))


class IsActiveManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)