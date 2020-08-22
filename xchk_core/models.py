from django.db import models
from django_enumfield import enum
import datetime
import pytz
import logging
import os
from django.conf import settings
logger = logging.getLogger(__name__)

class SubmissionState(enum.Enum):
    ACCEPTED = 0
    REFUSED = 1
    NOT_REACHED = 2 # can occur in case of technical error
    QUEUED = 3
    UNDECIDED = 4

class Repo(models.Model):
    url = models.CharField(null=False,blank=False,max_length=500)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='repos')
    # cursussen staan niet in de DB als data, dus kunnen niet linken via foreign key
    # de naam van de cursus moet dienen als referentie
    course = models.CharField(null=False,blank=False,max_length=500)

    def __str__(self):
        return f"repo van {self.user} voor {self.course}"

    class Meta:
        unique_together = [['user','course']]

class Submission(models.Model):
    checksum = models.CharField(max_length=40,null=True)
    timestamp = models.DateTimeField()
    repo = models.ForeignKey(Repo, null=False, on_delete=models.CASCADE)
    state = enum.EnumField(SubmissionState, default=SubmissionState.QUEUED)
    submitter = models.ForeignKey(settings.AUTH_USER_MODEL, null=False, on_delete=models.CASCADE)
    content_uid = models.CharField(max_length=200,null=False)

    def __str__(self):
        return f"poging van {self.submitter}" +\
               f" met state {self.state.name}," +\
               f" gecontroleerd op {self.timestamp},"+\
               f" met checksum {self.checksum}"
