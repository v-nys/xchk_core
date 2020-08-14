from config import celery_app
import channels.layers
from asgiref.sync import async_to_sync
from .models import Repo, SubmissionState, SubmissionV2
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
    submissions = [SubmissionV2.objects.get(id=submission_id) for submission_id in submission_ids]
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
        for mentioned_file in node.mentioned_files():
            mentioned_path = os.path.join(f'/tmp/submission{submission_id}',mentioned_file)
            if os.path.exists(mentioned_path):
                with open(mentioned_path) as fh:
                    single_file_result = (mentioned_file,'codelines',fh.readlines()) # code = algemene renderingstrategie? kan bv. zijn 'pygments',...
                result.append(single_file_result)
            else:
                result.append((mentioned_file,'',False)) # dus file is er gewoon niet
        return result
    except Exception as e:
        return "Iets misgelopen bij het ophalen van de verplichte bestanden. Kan een verkeerde filename zijn, kan een fout bij uitlezen files zijn."

# top priority for notification task
# might as well notify users immediately...
@celery_app.task(priority=9)
def notify_result(last_file_and_analysis,group_name):
    (last_file,analysis) = last_file_and_analysis
    channel_layer = channels.layers.get_channel_layer()
    async_to_sync(channel_layer.group_send)(group_name,
            {'type': 'completion',
             'last_reached_file': last_file,
             'analysis': analysis})

@celery_app.task(priority=9)
def notify_submitted_files(files,group_name):
    channel_layer = channels.layers.get_channel_layer()
    async_to_sync(channel_layer.group_send)(group_name,
            {'type': 'files', # tells consumer which callback to run
             'files': files}) # callback arg, will be either string or list
