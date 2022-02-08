import datetime
import os
import sys

import requests
from celery.schedules import crontab
from celery.task import periodic_task
from django.http import HttpResponse
from requests.auth import HTTPBasicAuth

from administration.models import SMSNotification, Integration, User, IntegrationData
from administration.statuses import SMSNotificationStatuses, ApplicationStatuses, IntegratedDataType
from core.celery import app
from core.settings import SMS_NOTIFICATION_API_BASE_URL
from exim import synchronization
from exim.models import IKRApplication, IKRApplicationStatusStep

import telebot
bot = telebot.TeleBot('1812368506:AAE6sqpZewP178Fzrr-k4Bhqkl4TjZtZR_Y')
chat_id = -1001481223731


@app.task
def synchronize_fss():
    errors = []
    try:
        synchronization.sync_russia()
    except Exception as e:
        errors.append(str(e))
    if errors:
        return errors
    return 'success'


@app.task
def reject_delayed_applications():
    try:
        applications = IKRApplication.objects.filter(is_active=False).exclude(status__in=[ApplicationStatuses.ZERO_ONE_NINE, ApplicationStatuses.ONE_ZERO_SIX])
        user = User.objects.get(username='a201283204')
        integration = Integration.objects.filter(organization_code='GTK',
                                                 data_type=IntegratedDataType.IKR_STATUS).last()

        status_json_data = {"KR_ST_Information": {"Information_Date": "",
                                                  "KR_ST": {
                                                      "RQST_NO": "",
                                                      "RQST_DT": "",
                                                      "DOC_FNCT_CD": "",
                                                      "PRICHINA": "",
                                                      "USER_FULL_NAME": "",
                                                      "USER_PHONE": "",
                                                      "USER_ACTION_DATE": "",
                                                      "USER_POSITION": "",
                                                      "USER_INN": "",
                                                      "ORGAN_ID": "",
                                                      "ORGAN_NAME": "",
                                                      "ORGAN_PHONE": ""
                                                  }
                                                  }
                            }
        status_json_data['KR_ST_Information']['Information_Date'] = datetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S")
        ikr_st = status_json_data['KR_ST_Information']['KR_ST']
        ikr_st['USER_FULL_NAME'] = user.name_ru
        ikr_st['USER_PHONE'] = user.phone
        ikr_st['USER_ACTION_DATE'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ikr_st['USER_POSITION'] = user.point.region.name_ru + 'карантин'
        ikr_st['USER_INN'] = str(user.tin)
        ikr_st['ORGAN_ID'] = user.point.region.gtk_code
        ikr_st['ORGAN_NAME'] = user.point.region.name_ru + 'карантин'
        ikr_st['ORGAN_PHONE'] = user.point.region.phone
        for application in applications:
            seconds_ago = (datetime.datetime.now() - application.added_at).total_seconds()
            if seconds_ago > 3600 * 24 * 9:
                ikr_st['RQST_NO'] = application.request_number
                ikr_st['RQST_DT'] = application.request_date.strftime("%Y-%m-%d")
                ikr_st[
                    'PRICHINA'] = 'Ўрнатилган тартибда кўриб чиқиш муддати тугаганлиги сабабли аризангиз қайтарилди. Илтимос, аризани қайтадан киритинг. Заявка отклонена по причине истечения установленного срока рассмотрения. Просим подать заявку заново.'
                ikr_st['DOC_FNCT_CD'] = '019'
                IntegrationData.objects.create(
                    integration=integration,
                    data=status_json_data
                )
                application.status = ApplicationStatuses.ZERO_ONE_NINE
                application.is_active = False
                application.is_paid = False
                application.save()
                IKRApplicationStatusStep.objects.create(
                    application=application,
                    status=ApplicationStatuses.ZERO_ONE_NINE,
                    description=ikr_st['PRICHINA'],
                    sender=user,
                )
        return 'success'
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        bot.send_message(chat_id=chat_id, text=f"exc_type: {exc_type}, fname: {fname}, exc_tb.tb_lineno: {exc_tb.tb_lineno}")
        return e


@periodic_task(run_every=datetime.timedelta(minutes=7), name="send_sms")
def send_sms():
    sms_notifications = SMSNotification.objects.filter(is_synchronised=False)
    for sms_notification in sms_notifications:
        request_body = {
            'messages': [
                {
                    'recipient': sms_notification.receiver_phone,
                    'message-id': sms_notification.message_id,
                    'sms': {
                        'originator': '3700',
                        'content': {
                            'text': sms_notification.text
                        }
                    }
                }
            ]
        }
        with requests.Session() as s:
            try:
                proxies = {'http': 'http://192.168.145.2:3128'}
                response = s.post(auth=HTTPBasicAuth('karantinuz', 'AB6ciQvf'),
                                  url=f'{SMS_NOTIFICATION_API_BASE_URL}send',
                                  json=request_body,
                                  proxies=proxies
                                  )

            except Exception as e:
                return HttpResponse(f'Exception: {e}')
        if response.text == 'Request is received':
            sms_notification.status = SMSNotificationStatuses.REQUESTED
        else:
            sms_notification.status = SMSNotificationStatuses.FAILED
        sms_notification.response = response.text
        sms_notification.is_synchronised = True
        sms_notification.save()
    return HttpResponse('Done')
