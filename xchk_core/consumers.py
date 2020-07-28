from channels.generic.websocket import WebsocketConsumer
import json
from .tasks import check_submission_batch, notify_result, retrieve_submitted_files, notify_submitted_files
from .models import Repo, SubmissionState, SubmissionV2
from django.utils import timezone
from django.db import transaction
import datetime
from asgiref.sync import async_to_sync
from . import contentviews, strats

class SubmittedFilesConsumer(WebsocketConsumer):

    def connect(self):
        # TODO: nagaan of het in principe beter is aparte groepnamen te gebruiken t.o.v. CheckRequest?
        self.group_name = f"user{self.scope['user'].id}"
        async_to_sync(self.channel_layer.group_add)(
            self.group_name,
            self.channel_name
        )
        self.accept()

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            self.group_name,
            self.channel_name
        )

    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        if self.scope['user'].is_superuser:
            retrieve_submitted_files.apply_async(args=[int(text_data_json['submission'])],link=notify_submitted_files.s(self.group_name),expires=300)

    def files(self, event):
        self.send(text_data=json.dumps({'files': event['files']}))

class CheckRequestConsumer(WebsocketConsumer):

    def connect(self):
        self.group_name = f"user{self.scope['user'].id}"
        async_to_sync(self.channel_layer.group_add)(
            self.group_name,
            self.channel_name
        )
        self.accept()

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            self.group_name,
            self.channel_name
        )

    def receive(self, text_data):
        print(text_data)
        text_data_json = json.loads(text_data)
        # TODO: giving task five minutes, may be able to come up with something more intelligent
        repo = Repo.objects.get(pk=int(text_data_json['repo']))
        exercises = [contentview for contentview in contentviews.all_contentviews if contentview.uid in text_data_json['exercises']]
        recent_submissions = SubmissionV2.objects.filter(submitter=self.scope['user']).filter(timestamp__gte=datetime.datetime.now() - datetime.timedelta(seconds=15))
        if len(recent_submissions) > 0 and not self.scope['user'].is_superuser:
            self.send(text_data=json.dumps({'last_reached_file': "geen bestand gecontroleerd", "analysis": [(None,None,None,"text","je mag maar één keer per vijftien seconden checken")]}))
            return
        batchtype = int(text_data_json['batchtype'])
        submissions = []
        with transaction.atomic():
            # TODO: is dit niet wat omslachtig? krijg de UID, ga hem omzetten naar een contentview, om dan hier toch maar gewoon id te geven?
            # kan gewoon de omzetting van data naar views overslaan? bekijk later
            for exercise in exercises:
                submission = SubmissionV2(checksum=None,
                                          timestamp=datetime.datetime.now(),
                                          repo=repo,
                                          state=SubmissionState.PENDING,
                                          submitter=self.scope['user'],
                                          # eigenlijk een class attribute maar kan er ook zo aan
                                          content_uid=exercise.uid)
                submission.save()
                submissions.append(submission)
        # need to represent repo / submission through their IDs because of serialization
        check_submission_batch.apply_async(args=[batchtype,\
                                                 repo.id,\
                                                 [submission.id for submission in submissions]],\
                                           link=notify_result.s(self.group_name),\
                                           expires=300)

    def completion(self, event):
        print(event)
        self.send(text_data=json.dumps({'last_reached_file': event['last_reached_file'], 'analysis': event['analysis']}))
