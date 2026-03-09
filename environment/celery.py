# path/to/your/proj/src/cfehome/celery.py
import os
from celery import Celery
from environment.base import set_environment

set_environment('MAIN')

app = Celery('environment')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()
