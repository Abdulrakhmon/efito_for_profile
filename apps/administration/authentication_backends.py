from django.contrib.auth.models import AnonymousUser
from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed

from administration.models import APIUser


class APIAbstractUser(AnonymousUser):

    def __init__(self, api_user):
        self.api_user = api_user

    @property
    def is_authenticated(self):
        return True


class APIUserAuthentication(authentication.BaseAuthentication):

    def authenticate(self, request):
        token = request.META.get("HTTP_AUTHORIZATION", None)
        if not token:
            raise AuthenticationFailed("Authentication token is required")

        try:
            _, token = token.split(' ')
        except:
            raise AuthenticationFailed("Invalid format ofr Authentication token")
        if _ != 'EfitoBearer':
            raise AuthenticationFailed("Invalid format ofr Authentication token")

        try:
            api_user = APIUser.objects.get(token=token)
        except APIUser.DoesNotExist:
            raise AuthenticationFailed("Invalid Token")
        return (APIUser(api_user), None)
