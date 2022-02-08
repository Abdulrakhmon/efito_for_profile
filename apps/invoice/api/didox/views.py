import os

import requests
from django.core.cache import cache
from django.http import HttpResponse
from django.views import View

from core import settings
from core.settings import proxy_config, BASE_DIR

import telebot

bot = telebot.TeleBot('1812368506:AAE6sqpZewP178Fzrr-k4Bhqkl4TjZtZR_Y')
chat_id = -1001481223731


class DidoxLoginView(View):

    def get(self, request):
        if not cache.get('didox_signed_in_token'):
            quarantine_tin_signature = os.path.join(os.path.join(BASE_DIR, 'certificates'),
                                                    'quarantine_tin_signature.pem')
            try:
                with open(quarantine_tin_signature, 'rb') as f:
                    quarantine_tin_signature = f.read()

                didox_signed_in_token_response = requests.post(
                    os.environ.get('DIDOX_API_BASE_URL') + '/v1/auth/201283204/token/ru',
                    data={
                        "signature": quarantine_tin_signature
                    },
                    proxies=proxy_config,
                    headers={'Content-Type': 'application/x-www-form-urlencoded'},
                    verify=False)

                cache.set('didox_signed_in_token', didox_signed_in_token_response.json().get('token'),
                          timeout=settings.DIDOX_TOKENS_TIMEOUT)

                return HttpResponse(didox_signed_in_token_response)
            except Exception as e:
                bot.send_message(chat_id=chat_id, text=e)
        else:
            return HttpResponse(status=200)


class DidoxProfileView(View):

    def get(self, request, **kwargs):
        response = None
        try:
            profile_response = requests.get(
                os.environ.get('DIDOX_API_BASE_URL') + f'/v1/profile/{kwargs["tin"]}?document_date=',
                proxies=proxy_config,
                headers={'api-key': cache.get('didox_signed_in_token'),
                         'user-key': cache.get('didox_signed_in_token'),
                         'Content-Type': 'application/json'},
                verify=False)
            return HttpResponse(profile_response)
        except Exception as e:
            bot.send_message(chat_id=chat_id, text=e)
            return HttpResponse(status=500)
