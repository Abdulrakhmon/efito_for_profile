from __future__ import absolute_import
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'efito_for_profile.settings')
app = Celery('efito_for_profile')
app.config_from_object('django.conf:settings')
# app.config_from_object('efito_for_profile.settings')

app.conf.beat_schedule = {
    # Executes every Monday morning at 7:30 a.m.
    'send_fss_russia_every_5_am': {
        'task': 'exim.tasks.synchronize_fss',
        'schedule': crontab(hour=5, minute=0),
    },
    'reject_delayed_applications_every_7_am': {
        'task': 'exim.tasks.reject_delayed_applications',
        'schedule': crontab(hour=7, minute=0),
    },

}

app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
