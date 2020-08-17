from channels.generic.websocket import WebsocketConsumer
import json
from .tasks import check_submission_batch, notify_result
from .models import Repo, SubmissionState, Submission
from django.utils import timezone
from django.db import transaction
import datetime
from asgiref.sync import async_to_sync
from . import contentviews, strats

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
        # TODO: can simplify now that exercises are checked one by one
        text_data_json = json.loads(text_data)
        # TODO: giving task five minutes, may be able to come up with something more intelligent
        repo = Repo.objects.get(pk=int(text_data_json['repo']))
        # FIXME: there should be exactly one exercise...
        exercises = [contentview for contentview in contentviews.all_contentviews() if contentview.uid == text_data_json['exercise']]
        recent_submissions = Submission.objects.filter(submitter=self.scope['user']).filter(timestamp__gte=datetime.datetime.now() - datetime.timedelta(seconds=15))
        if len(recent_submissions) > 0 and not self.scope['user'].is_superuser:
            self.send(text_data=json.dumps({'last_reached_file': "geen bestand gecontroleerd", "analysis": [(None,None,None,"text","je mag maar één keer per vijftien seconden checken")]}))
            return
        submissions = []
        with transaction.atomic():
            # TODO: is dit niet wat omslachtig? krijg de UID, ga hem omzetten naar een contentview, om dan hier toch maar gewoon id te geven?
            # kan gewoon de omzetting van data naar views overslaan? bekijk later
            for exercise in exercises:
                submission = Submission(checksum=None,
                                          timestamp=datetime.datetime.now(),
                                          repo=repo,
                                          state=SubmissionState.QUEUED,
                                          submitter=self.scope['user'],
                                          # eigenlijk een class attribute maar kan er ook zo aan
                                          content_uid=exercise.uid)
                submission.save()
                submissions.append(submission)
        # need to represent repo / submission through their IDs because of serialization
        check_submission_batch.apply_async(args=[repo.id,\
                                                 [submission.id for submission in submissions]],\
                                           link=notify_result.s(self.group_name),\
                                           expires=300)

    def completion(self, event):
        strategy_analysis = strats.StrategyAnalysis(*event['strategy_analysis'])
        state = strategy_analysis.submission_state
        if state == SubmissionState.ACCEPTED:
            message = "Je oefening is aanvaard."
        elif state == SubmissionState.REFUSED:
            message = "Je oefening is geweigerd. Inspecteer de gemarkeerde technische vereisten. Contacteer zo nodig de lector nadat je dit hebt gedaan."
        elif state == SubmissionState.NOT_REACHED:
            message = "Er is een technische fout opgetreden tijdens het verwerken van je oefening. Dit kan aan jouw oplossing liggen, maar het kan ook een storing zijn. Klik op de rode knop onderaan en stuur de getoonde informatie naar de lector."
        elif state == SubmissionState.UNDECIDED:
            message = "Je oefening is voorlopig aanvaard. Het systeem heeft ze nog niet leren herkennen als juist of fout. Je mag voorlopig verder en de lector zal je oefening met de hand nakijken."
        else:
            message = "Onbekende toestand. Klik op de rode knop onderaan en stuur de getoonde informatie naar de lector."
        self.send(text_data=json.dumps({'message': message, 'show_contact_button': state not in [SubmissionState.ACCEPTED, SubmissionState.UNDECIDED], 'components': event['components'], 'url': strategy_analysis.submission_url, 'checksum': strategy_analysis.submission_checksum}))
