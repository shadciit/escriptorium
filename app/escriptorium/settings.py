"""
Django settings for escriptorium project.

Generated by 'django-admin startproject' using Django 2.1.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""

import os
import subprocess
import sys

from django.utils.translation import gettext_lazy as _
from kombu import Queue
from kraken.kraken import SEGMENTATION_DEFAULT_MODEL

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

ADMINS = [(os.getenv('DJANGO_SU_NAME', 'admin'),
           os.getenv('DJANGO_SU_EMAIL', 'admin@example.com'))]

# Add apps directory the sys.path
APPS_DIR = os.path.join(BASE_DIR, 'apps')
sys.path.append(APPS_DIR)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SITE_ID = 1
SECRET_KEY = os.getenv('SECRET_KEY', 'a-beautiful-snowflake')

# SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', False) == 'True'  # should be done by  nginx
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', False)

CUSTOM_HOME = os.getenv('CUSTOM_HOME', False) == 'True'

ALLOWED_HOSTS = ['*']

ASGI_APPLICATION = "escriptorium.routing.application"

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.forms',

    'django_cleanup',
    'ordered_model',
    'easy_thumbnails',
    'easy_thumbnails.optimize',
    'channels',
    'rest_framework',
    'rest_framework.authtoken',
    'captcha',

    'bootstrap',
    'versioning',
    'users',
    'core',
    'imports',
    'reporting',
    'django_prometheus',
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

PROMETHEUS_EXPORT_MIGRATIONS = False

ROOT_URLCONF = 'escriptorium.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(PROJECT_ROOT, 'templates'),
                 os.path.join(BASE_DIR, 'homepage')],  # custom homepage dir (volume in docker)
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'escriptorium.context_processors.enable_cookie_consent',
                'escriptorium.context_processors.custom_homepage'
            ],
        },
    },
]

# Allow to use the ColorField in the admin
FORM_RENDERER = 'django.forms.renderers.TemplatesSetting'

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

WSGI_APPLICATION = 'escriptorium.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': os.getenv('SQL_ENGINE', 'django.db.backends.postgresql'),
        'NAME': os.getenv('POSTGRES_DB', 'escriptorium'),
        'USER': os.getenv('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'postgres'),
        'HOST': os.getenv('SQL_HOST', 'localhost'),
        'PORT': os.getenv('SQL_PORT', '5432'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTH_USER_MODEL = 'users.User'
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'projects-list'
LOGOUT_REDIRECT_URL = '/'

# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True
LANGUAGES = [
    ('en', _('English')),
    ('de', _('French')),
]

EMAIL_HOST = os.getenv('EMAIL_HOST', 'mail')
EMAIL_PORT = os.getenv('EMAIL_PORT', 25)
DEFAULT_FROM_EMAIL = os.getenv('DJANGO_FROM_EMAIL', 'noreply@escriptorium.fr')

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://%s:%d/1" % (REDIS_HOST, REDIS_PORT),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient"
        },
        "KEY_PREFIX": "cache"
    }
}

ELASTICSEARCH_HOST = os.getenv('ELASTICSEARCH_HOST', 'localhost')
ELASTICSEARCH_PORT = os.getenv('ELASTICSEARCH_HOST', 9200)

CELERY_BROKER_URL = 'redis://%s:%d/0' % (REDIS_HOST, REDIS_PORT)
CELERY_RESULT_BACKEND = 'redis://%s:%d' % (REDIS_HOST, REDIS_PORT)
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACKS_LATE = True

# time in seconds a user has to wait after a task is started before being able to recover
TASK_RECOVER_DELAY = 60 * 60 * 24  # 1 day

CELERY_TASK_QUEUES = (
    Queue('default', routing_key='default'),
    Queue('live', routing_key='live'),  # for everything that needs to be done on the spot to update the ui
    Queue('low-priority', routing_key='low-priority'),
    Queue('gpu', routing_key='gpu'),  # for everything that could use a GPU
)
CELERY_TASK_DEFAULT_QUEUE = 'default'
# When updating 'gpu' queue don't forget to add or remove the GPU quota check in the affected tasks
CELERY_TASK_ROUTES = {
    # 'core.tasks.*': {'queue': 'default'},
    'core.tasks.recalculate_masks': {'queue': 'live'},
    'core.tasks.generate_part_thumbnails': {'queue': 'low-priority'},
    'core.tasks.train': {'queue': 'gpu'},
    'core.tasks.segtrain': {'queue': 'gpu'},
    # 'escriptorium.celery.debug_task': '',
    'imports.tasks.*': {'queue': 'low-priority'},
    'users.tasks.async_email': {'queue': 'low-priority'},
}

REPORTING_TASKS_BLACKLIST = [
    'users.tasks.async_email',
]

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(REDIS_HOST, REDIS_PORT)],
        },
    },
}
# fixes https://github.com/django/channels/issues/1240:
DATA_UPLOAD_MAX_MEMORY_SIZE = 150 * 1024 * 1024  # value in bytes (so 150Mb)


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

FRONTEND_DIR = os.getenv('FRONTEND_DIR', os.path.join(BASE_DIR, '..', 'front', 'dist'))

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATICFILES_DIRS = [
    os.path.join(PROJECT_ROOT, 'static'),
    FRONTEND_DIR
]

if CUSTOM_HOME:
    # custom homepage directory
    STATICFILES_DIRS.append(os.path.join(BASE_DIR, 'homepage'))

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'formatters': {
        'django.server': {
            '()': 'django.utils.log.ServerFormatter',
            'format': '[{server_time}] {message}',
            'style': '{',
        }
    },
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(PROJECT_ROOT, 'logs', 'error.log'),
        },
        'console': {
            'level': 'ERROR',
            'class': 'logging.StreamHandler',
        },
        'django.server': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'django.server',
        },
        'mail_admins': {
            'level': 'ERROR',
            # 'filters': ['require_debug_false'],  # make sure to set EMAIL_BACKEND
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'kraken': {
            'handlers': ['console', 'mail_admins'],
            'propagate': True,
        },
        'core': {
            'handlers': ['file', 'console', 'mail_admins'],
            'propagate': False,
        },
        'django': {
            'handlers': ['file', 'console', 'mail_admins']
        },
        'django.server': {
            'handlers': ['django.server'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['django.server'],
        }
    },
}

COMPRESS_ENABLE = True
ALWAYS_CONVERT = False

FILE_UPLOAD_PERMISSIONS = 0o644
THUMBNAIL_ENABLE = True
THUMBNAIL_ALIASES = {
    '': {
        'list': {'size': (50, 50), 'crop': 'center'},
        'card': {'size': (180, 180), 'crop': 'smart'},
        'large': {'size': (1000, 1000), 'crop': False, 'upscale': False}
    }
}
# THUMBNAIL_OPTIMIZE_COMMAND = {
#     'png': '/usr/bin/optipng {filename}',
#     # 'gif': '/usr/bin/optipng {filename}',
#     'jpeg': '/usr/bin/jpegoptim -S200 {filename}'
# }


ENABLE_COOKIE_CONSENT = os.getenv('ENABLE_COOKIE_CONSENT', True)

VERSIONING_DEFAULT_SOURCE = 'eScriptorium'

VERSION_DATE = os.getenv('VERSION_DATE', '<development>')
KRAKEN_VERSION = subprocess.getoutput('kraken --version')

IIIF_IMPORT_QUALITY = 'full'

KRAKEN_TRAINING_DEVICE = os.getenv('KRAKEN_TRAINING_DEVICE', 'cpu')
KRAKEN_TRAINING_LOAD_THREADS = int(os.getenv('KRAKEN_TRAINING_LOAD_THREADS', 0))
KRAKEN_DEFAULT_SEGMENTATION_MODEL = SEGMENTATION_DEFAULT_MODEL

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        # 'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly'
        'rest_framework.permissions.IsAuthenticated'
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        # 'rest_framework.authentication.BasicAuthentication',  # Only for testing
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PAGINATION_CLASS': 'core.pagination.CustomPagination',
    'PAGE_SIZE': 10,
}

DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000

if 'test' in sys.argv:
    try:
        from .test_settings import *  # noqa F401
    except (ModuleNotFoundError, ImportError):
        pass

CPU_COST_FACTOR = os.getenv('CPU_COST_FACTOR', 1.0)
GPU_COST = os.getenv('GPU_COST', 1.0)

# Boolean used to defuse quotas enforcement
DISABLE_QUOTAS = os.getenv('DISABLE_QUOTAS', "True").lower() not in ("false", "0")

# Limitation of disk storage usage per user, should be defined as a positive integer in Mb
# If set to None, users have unlimited disk storage capacity
QUOTA_DISK_STORAGE = int(os.environ['QUOTA_DISK_STORAGE']) if os.environ.get('QUOTA_DISK_STORAGE') else None

# Limitation of CPU minutes usage per user over a week, should be defined as a positive integer in CPU-min
# If set to None, users have unlimited CPU minutes capacity
QUOTA_CPU_MINUTES = int(os.environ['QUOTA_CPU_MINUTES']) if os.environ.get('QUOTA_CPU_MINUTES') else None

# Limitation of GPU minutes usage per user over a week, should be defined as a positive integer in GPU-min
# If set to None, users have unlimited GPU minutes capacity
QUOTA_GPU_MINUTES = int(os.environ['QUOTA_GPU_MINUTES']) if os.environ.get('QUOTA_GPU_MINUTES') else None

# Number of days that we have to wait before sending a new email to an user that reached one or more of its quotas
QUOTA_NOTIFICATIONS_TIMEOUT = int(os.environ.get('QUOTA_NOTIFICATIONS_TIMEOUT', '3'))

# Boolean used to enable the OpenITI mARkdown export mode
EXPORT_OPENITI_MARKDOWN_ENABLED = os.getenv('EXPORT_OPENITI_MARKDOWN', "False").lower() not in ("false", "0")

# Boolean used to enable the OpenITI TEI XML export mode
EXPORT_TEI_XML_ENABLED = os.getenv('EXPORT_TEI_XML', "False").lower() not in ("false", "0")
