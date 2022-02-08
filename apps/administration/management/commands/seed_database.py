from time import sleep

from django.core.management import BaseCommand, CommandError
from ..utils import database_seeders
from ...models import Country, HSCode, Unit, Point, Region, District, User


class Command(BaseCommand):
    help = 'It will seed database automatically with initial data'

    def handle(self, *args, **options):
        try:
            Country.objects.all().delete()
            Region.objects.all().delete()
            District.objects.all().delete()
            Point.objects.all().delete()
            Unit.objects.all().delete()
            User.objects.all().delete()
            HSCode.objects.all().delete()
        except:
            raise CommandError('Something went wrong')
