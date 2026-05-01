"""
WSGI config for the motorbike_rental project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "motorbike_rental.settings")

application = get_wsgi_application()
