from .base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'cbz)hjv)qg%4zuud5hxp-#tss860!2^^@r6ruqa%jurhbnlu8f'

DEBUG = True

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

INSTALLED_APPS += (
    'debug_toolbar',
)

DEFAULT_FROM_EMAIL = ''

INTERNAL_IPS = ('127.0.0.1',)
