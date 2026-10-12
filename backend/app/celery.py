import os
from celery import Celery

from app.settings import CELERY

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

app = Celery("dzen")

app.config_from_object("django.conf:settings", namespace="CELERY")
app.config_from_object(CELERY)

app.autodiscover_tasks()
