"""
WSGI config for bonus project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os
from decouple import config

from django.core.wsgi import get_wsgi_application

# Check for "production" and load settings if found
if config('DJANGO_ENVIRONMENT') == 'production':
    os.environ['DJANGO_SETTINGS_MODULE'] = 'bonus.settings.production'
else:  # Else go with development
    os.environ['DJANGO_SETTINGS_MODULE'] = 'bonus.settings.development'

application = get_wsgi_application()
