import os
import sys

path = os.path.expanduser('~/bonus') # Replace with your app path
if path not in sys.path:
    sys.path.append(path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'bonus.settings' # Replace with your project name

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()