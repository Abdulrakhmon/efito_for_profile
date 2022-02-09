"""
Django settings for efito_for_profile project.

Generated by 'django-admin startproject' using Django 2.2.7.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

import os
import sys
import environ
from datetime import date
from django.contrib.messages import constants as message_constants

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
environ.Env.read_env()
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(BASE_DIR, 'apps'))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY')

ALLOWED_HOSTS = ['*']

DEBUG = False if os.environ.get('DEBUG') == 'False' else True
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    #  apps
    'administration.apps.AdministrationConfig',
    'exim.apps.ExImConfig',
    'invoice.apps.InvoiceConfig',
    'lab.apps.LabConfig',
    'fumigation.apps.FumigationConfig',
    'monitoring.apps.MonitoringConfig',
    'ppp.apps.PppConfig',

    #  third party apps
    'rest_framework',
    'rest_framework.authtoken',  # <-- Here
    'rest_framework_xml',
    'debug_toolbar',
    'qr_code',
    'corsheaders',
    'mathfilters',
    'django.contrib.humanize',

]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'administration.middlewares.LoginRequiredMiddleware',
    'administration.middlewares.PointRequiredMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

CORS_ORIGIN_ALLOW_ALL = True

ROOT_URLCONF = 'efito_for_profile.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # 'administration.management.utils.context_processors.ikr_template_variables'
            ],
        },
    },
]
# https://www.alpharithms.com/django-postgresql-install-tutorial-123816/
DATABASES = {
    'default': {
        # 'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        # 'ENGINE': 'django.db.backends.sqlite3',
        'ENGINE': os.environ.get('DATABASE_ENGINE'),
        'NAME': os.environ.get('DATABASE_NAME'),
        'USER': os.environ.get('DATABASE_USER'),
        'PASSWORD': os.environ.get('DATABASE_PASSWORD'),
        'HOST': os.environ.get('DATABASE_HOST'),
        'PORT': os.environ.get('DATABASE_PORT')
    }
}

WSGI_APPLICATION = 'efito_for_profile.wsgi.application'

# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    # {
    #     'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    # },
    # {
    #     'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    # },
    # {
    #     'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    # },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# REST_FRAMEWORK = {
#     'DEFAULT_PERMISSION_CLASSES': [
#         'administration.api.permissions.IPAddressPermission',
#     ]
# }

# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Tashkent'

USE_I18N = True

USE_L10N = True

# USE_TZ = True

AUTH_USER_MODEL = 'administration.User'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

STATIC_URL = '/static/'
# STATIC_ROOT = 'static/'
STATICFILES_DIRS = [
    BASE_DIR + '/static/'
]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# DataFlair #Logging Information
LOGGING = {
    'version': 1,
    # Version of logging
    'disable_existing_loggers': False,
    # disable logging
    # Handlers #############################################################
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'common.log'),
            'when': 'midnight',
            'delay': True,
            'interval': 1,
            'formatter': 'verbose',
            'backupCount': 50,  # keep at most 10 day log files
        },
        # ########################################################################
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    # Loggers ####################################################################
    'loggers': {
        '': {
            'handlers': ['file'],
            'level': 'INFO',
        }
    },
}

LOGIN_NOT_REQUIRED_URL_NAMES = ['static', 'media', 'get_ikr', 'shipment_confirm', 'download_import_protocol',
                                'check_ikr', 'update_ikr', 'send_akd', 'invoice_index', 'print_akd_invoice',
                                'print_invoice', 'add_akd_application', 'add_export_fss_application', 'didox_login',
                                'download_invoice', 'get_akd', 'get_fss', 'get_notification_status', 'print_local_fss',
                                'add_import_fss', 'check_certificate', 'download_export_fss', 'check_certificate_form',
                                'download_akd', 'download_local_fss', 'print_local_fss', 'munis_check', 'munis_api',
                                'download_certificate_of_disinfestation', 'organization_name', 'add_ikr_application',
                                'download_certificate_of_disinfestation_old_version', 'download_ikr_pdf_version',
                                'add_ikr_renewal_application', 'CheckFumigationCertificateFromOldEfito', 'didox_profile',
                                'send_fss_manually_to_ru', 'add_local_fss_application', 'api_token_auth',
                                'pdf_of_ppp_registration_protocol']

LOGIN_NOT_REQUIRED_NAMESPACES = ['admin', 'administration', 'bot', 'lab', 'ppp']
FILE_UPLOAD_PERMISSIONS = 0o644
ALLOWED_HOSTS_FOR_API = ['127.0.0.1']

FIRST_DATE_OF_CURRENT_YEAR = date(date.today().year, 1, 1).strftime('%Y-%m-%d')
TIME_FOR_SHIPMENT = 864000
TIME_FOR_TEMPORARILY_STOPPED_SHIPMENT = 259200

TIME_FOR_CHANGE_IKRSHIPMENT = 518400  # why we need to give a short period if VED inspector can edit
ONE_BASIC_ESTIMATE = 270000  # Одна базовая расчетная величина or  Bazaviy hisoblash
LAB_DEFAULT_EXPENSE = 88563  # Одна базовая расчетная величина or  Bazaviy hisoblash
LATIN_TO_CYRILLIC = {
    "A": "&#1040;",
    "B": "&#1041;",
    "V": "&#1042;",
    "G": "&#1043;",
    "D": "&#1044;",
    "Ye": "&#1045;",
    "YE": "&#1045;",
    "J": "&#1046;",
    "Z": "&#1047;",
    "I": "&#1048;",
    "Y": "&#1049;",
    "K": "&#1050;",
    "L": "&#1051;",
    "M": "&#1052;",
    "N": "&#1053;",
    "O": "&#1054;",
    "P": "&#1055;",
    "R": "&#1056;",
    "S": "&#1057;",
    "T": "&#1058;",
    "U": "&#1059;",
    "F": "&#1060;",
    "X": "&#1061;",
    "Ts": "&#1062;",
    "TS": "&#1062;",
    "Ch": "&#1063;",
    "CH": "&#1063;",
    "Sh": "&#1064;",
    "SH": "&#1064;",
    "EE": "&#1069;",
    "Yu": "&#1070;",
    "YU": "&#1070;",
    "Ya": "&#1071;",
    "YA": "&#1071;",
    "G'": "&#1170;",
    "O'": "&#1038;",
    "O’": "&#1038;",
    "Yo": "&#1025;",
    "YO": "&#1025;",
    "Q": "&#1178;",
    "H": "&#1202;",
    "a": "&#1072;",
    "b": "&#1073;",
    "v": "&#1074;",
    "g": "&#1075;",
    "d": "&#1076;",
    "ye": "&#1077;",
    "yE": "&#1077;",
    "j": "&#1078;",
    "z": "&#1079;",
    "i": "&#1080;",
    "y": "&#1081;",
    "k": "&#1082;",
    "l": "&#1083;",
    "m": "&#1084;",
    "n": "&#1085;",
    "o": "&#1086;",
    "p": "&#1087;",
    "r": "&#1088;",
    "s": "&#1089;",
    "t": "&#1090;",
    "u": "&#1091;",
    "f": "&#1092;",
    "x": "&#1093;",
    "ts": "&#1094;",
    "tS": "&#1094;",
    "ch": "&#1095;",
    "cH": "&#1095;",
    "sh": "&#1096;",
    "sH": "&#1096;",
    "'": "&#1098;",
    "ee": "&#1101;",
    "eE": "&#1101;",
    "e": "&#1077;",
    "E": "&#1069;",
    "yu": "&#1102;",
    "yU": "&#1102;",
    "ya": "&#1103;",
    "yA": "&#1103;",
    "o'": "&#1118;",
    "q": "&#1179;",
    "g'": "&#1171;",
    "yo": "&#1105;",
    "yO": "&#1105;",
    "h": "&#1203;",
    " ": " ",
    "-": "-",
}
MESSAGE_TAGS = {message_constants.DEBUG: 'debug',
                message_constants.INFO: 'info',
                message_constants.SUCCESS: 'success',
                message_constants.WARNING: 'warning',
                message_constants.ERROR: 'danger'}

INTERNAL_IPS = [
    # ...
    # '127.0.0.1',
    # ...
]

DEBUG_TOOLBAR_PANELS = [
    'debug_toolbar.panels.versions.VersionsPanel',
    'debug_toolbar.panels.timer.TimerPanel',
    'debug_toolbar.panels.settings.SettingsPanel',
    'debug_toolbar.panels.headers.HeadersPanel',
    'debug_toolbar.panels.request.RequestPanel',
    'debug_toolbar.panels.sql.SQLPanel',
    'debug_toolbar.panels.staticfiles.StaticFilesPanel',
    'debug_toolbar.panels.templates.TemplatesPanel',
    'debug_toolbar.panels.cache.CachePanel',
    'debug_toolbar.panels.signals.SignalsPanel',
    'debug_toolbar.panels.logging.LoggingPanel',
    'debug_toolbar.panels.redirects.RedirectsPanel',
    'debug_toolbar.panels.profiling.ProfilingPanel',
]
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10240

#   Redis installation --> https://phoenixnap.com/kb/install-redis-on-mac
BROKER_URL = 'redis://localhost:6379'
# BROKER_URL = f'amqp://{os.environ.get("RABBITMQ_USER")}:' \
#              f'{os.environ.get("RABBITMQ_PASSWORD")}@localhost:5672/' \
#              f'{os.environ.get("RABBITMQ_VHOST")}'
CELERY_TIMEZONE = 'Asia/Tashkent'
CELERY_ENABLE_UTC = False
CELERY_IMPORTS = (
    'administration.tasks',
    'exim.ephyto.tasks',
    'invoice.api.munis_webservice.tasks'
)
SMS_NOTIFICATION_API_BASE_URL = 'http://91.204.239.44/broker-api/'
SMS_NOTIFICATION_ORIGINATOR = '3700'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',  # <-- And here
    ],
    'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.coreapi.AutoSchema',
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework_xml.parsers.XMLParser',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework_xml.renderers.XMLRenderer',
    ],
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": BROKER_URL,
    }
}

http_proxy_url = os.getenv('PROXY_HTTP')
https_proxy_url = os.getenv('PROXY_HTTPS')

proxy_config = {
    'http': http_proxy_url,
    'https': https_proxy_url
}

EXPERT_FSS_PRICES = [ONE_BASIC_ESTIMATE, ONE_BASIC_ESTIMATE / 4, ONE_BASIC_ESTIMATE / 5, ONE_BASIC_ESTIMATE * 15 / 100]

DIDOX_TOKENS_TIMEOUT = 10800