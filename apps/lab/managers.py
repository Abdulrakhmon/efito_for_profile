from django.db.models import Manager


class IsApprovedManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_approved=True)