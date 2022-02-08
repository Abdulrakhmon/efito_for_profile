from django.contrib import messages
from django.contrib.auth import logout
from django.utils.deprecation import MiddlewareMixin
from django.urls import resolve, reverse
from django.http import HttpResponseRedirect
from core.settings import LOGIN_NOT_REQUIRED_URL_NAMES, LOGIN_NOT_REQUIRED_NAMESPACES


class LoginRequiredMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if not request.user.is_authenticated:
            resolved_url = resolve(request.path_info)
            if not (resolved_url.url_name in LOGIN_NOT_REQUIRED_URL_NAMES or
                    resolved_url.namespace in LOGIN_NOT_REQUIRED_NAMESPACES):
                return HttpResponseRedirect(reverse('administration:login'))


class PointRequiredMiddleware(MiddlewareMixin):
    def process_request(self, request):
        user = request.user
        if user.is_authenticated:
            if not user.point:
                if resolve(request.path_info).namespace != 'admin':
                    logout(request)
                    messages.warning(request, 'Вас нет разрешения на вход в эту панель')
                    return HttpResponseRedirect(reverse('administration:login'))
