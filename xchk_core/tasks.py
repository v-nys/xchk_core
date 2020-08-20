from config import celery_app
import channels.layers
from asgiref.sync import async_to_sync
from .models import Repo, SubmissionState, Submission
from . import contentviews, courses, strats
from .strats import OutcomeAnalysis, OutcomeComponent

import os
import subprocess
from contextlib import redirect_stdout
import environ
import logging
import time
from django.db import transaction

logger = logging.getLogger(__name__)

STUDENT_SOLUTION_DIR = '/tmp/studentrepo'

############################################
#              !!! OPGELET !!!             #
# DEZE TASKS VERONDERSTELLEN CONCURRENCY 1 #
#              !!! OPGELET !!!             #
############################################

def _check_submissions_in_commit(submissions,checksum):
    (strategy_analysis, components_analysis) = (None,[])
    for submission in submissions:
        # FIXME: dit is snelle test
        # kan zijn dat foute UID is ingegeven (weliswaar alleen door geknoei van studenten of update server)
        # TODO: kan ik dit efficiënter maken door niet meteen de volledige lijst op te bouwen en enkel eerste elemen van lazy list te nemen? bespaart check accessibility...
        eligible_exercises = [content for content in contentviews.all_contentviews() if content.uid == submission.content_uid and content.is_accessible_by(submission.submitter)]
        exercise = eligible_exercises[0]
        submission.checksum = checksum
        if strategy_analysis is None or strategy_analysis.submission_state == SubmissionState.ACCEPTED:
            strategy = exercise.strat
            (strategy_analysis,components_analysis) = strategy.check_submission(submission,STUDENT_SOLUTION_DIR)
            submission.state = strategy_analysis.submission_state
        submission.save()
    return (strategy_analysis,components_analysis)

@celery_app.task(priority=0)
def check_submission_batch(repo_id,submission_ids,*args,**kwargs):
    # all id's have been queried by consumer, so assume they are okay
    repo = Repo.objects.get(id=repo_id)
    subprocess.run(f'rm -rf {STUDENT_SOLUTION_DIR}',shell=True)
    subprocess.run(f'git clone {repo.url} {STUDENT_SOLUTION_DIR}',shell=True)
    subprocess.run(f'chmod -R 777 {STUDENT_SOLUTION_DIR}',shell=True)
    checksum = subprocess.run(f'cd {STUDENT_SOLUTION_DIR} ; git rev-parse HEAD',\
                              shell=True,\
                              capture_output=True).stdout.decode('utf-8').strip()
    submissions = [Submission.objects.get(id=submission_id) for submission_id in submission_ids]
    if len(checksum) == 40:
        return _check_submissions_in_commit(submissions,checksum)
    else:
        submissions[0].state = SubmissionState.NOT_REACHED
        submission[0].save()
        return (StrategyAnalysis(submission_state=SubmissionState.NOT_REACHED,submission_url=submissions[0].repo.url,submission_checksum=checksum),[])

@celery_app.task(priority=1)
def retrieve_submitted_files(submission_id,*args,**kwargs):
    submission = Submission.objects.get(id=submission_id)
    node = submission.exercise
    repo = submission.repo
    subprocess.run(f'rm -rf /tmp/submission{submission_id}',shell=True)
    subprocess.run(f'git clone {repo.url} /tmp/submission{submission_id}',shell=True)
    subprocess.run(f'cd /tmp/submission{submission_id}; git checkout {submission.checksum}',shell=True)
    try:
        result = []
        return result
    except Exception as e:
        return "Iets misgelopen bij het ophalen van de verplichte bestanden. Kan een verkeerde filename zijn, kan een fout bij uitlezen files zijn."

# top priority for notification task
# might as well notify users immediately...
@celery_app.task(priority=9)
def notify_result(strategy_analysis_and_components,group_name):
    (strategy_analysis,components) = strategy_analysis_and_components
    channel_layer = channels.layers.get_channel_layer()
    async_to_sync(channel_layer.group_send)(group_name,
            {'type': 'completion',
             'strategy_analysis': strategy_analysis,
             'components': components})

@celery_app.task(priority=9)
def notify_submitted_files(files,group_name):
    channel_layer = channels.layers.get_channel_layer()
    async_to_sync(channel_layer.group_send)(group_name,
            {'type': 'files', # tells consumer which callback to run
             'files': files}) # callback arg, will be either string or list
