from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/sock/$', consumers.CheckRequestConsumer),
    re_path(r'ws/submissionsock/$', consumers.SubmittedFilesConsumer),
]
