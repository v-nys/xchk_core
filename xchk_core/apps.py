from django.apps import AppConfig
from django.db.models.signals import post_migrate


class CheckerappConfig(AppConfig):
    name = 'xchk'

    def ready(self):
        from .signals import handlers

