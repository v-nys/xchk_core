from config import celery_app
import channels.layers
from asgiref.sync import async_to_sync
from .models import Repo, SubmissionState, SubmissionV2
from . import contentviews, courses, strats

import os
import subprocess
from contextlib import redirect_stdout
import environ
import logging
import time
from django.db import transaction

logger = logging.getLogger(__name__)

MODEL_SOLUTION_DIR = '/tmp/modeloplossingen'
STUDENT_SOLUTION_DIR = '/tmp/studentrepo'

############################################
#              !!! OPGELET !!!             #
# DEZE TASKS VERONDERSTELLEN CONCURRENCY 1 #
#              !!! OPGELET !!!             #
############################################

def _check_submissions_in_commit(submissions,checksum,batchtype_id):
    batchtype = strats.batch_types[batchtype_id]
    (exit_code, analysis) = (None,None)
    first_failed_or_unreached_submission = None
    for submission in submissions:
        # FIXME: dit is snelle test
        # kan zijn dat foute UID is ingegeven (weliswaar alleen door geknoei van studenten of update server)
        # is_accessible_by kan niet meer per node voorzien worden
        # maar kan wel per contentview voorzien worden
        eligible_exercises = [content for content in contentviews.all_contentviews if content.uid == submission.content_uid]
        exercise = eligible_exercises[0]
        try:
            submission.checksum = checksum
            if exit_code is None or exit_code == SubmissionState.ACCEPTED:
                strategy = exercise.strat
                # first check whether all checks are allowed using batch type
                for check in strategy.component_checks():
                    allowed = False
                    for allowed_check in batchtype.allowed_checks:
                        allowed = allowed or (check == allowed_check)
                    if not allowed:
                        # format analysis
                        # 1) number of problematic instruction in instruction parse tree under depth-first traversal, ignoring negations, using None for other errors
                        # 2) expected outcome (actual outcome is implied: inverse)
                        # 3) format name for extra explanation (or None if explanation is None)
                        # 4) explanation in said format (or None)
                        (exit_code,analysis) = (SubmissionState.NOT_REACHED,[(None,None,None,"text","Minstens één uit te voeren controle is niet toegelaten door het batchtype.")])
                # if all checks are allowed, check this submission
                if exit_code is None or exit_code == SubmissionState.ACCEPTED:
                    (exit_code,analysis) = exercise.strat.check_submission(submission,STUDENT_SOLUTION_DIR,MODEL_SOLUTION_DIR)
                    submission.state = exit_code
                if exit_code is not None and exit_code != SubmissionState.ACCEPTED:
                    first_failed_or_unreached_submission = submission
            else:
                submission.state = SubmissionState.NOT_REACHED
        except Exception as e:
            logger.exception('Fout bij controle submissie: %s',e)
            analysis = [(None,None,None,"text","Er is iets fout gelopen, meld aan de lector.")]
            submission.state = SubmissionState.NOT_REACHED
            if not first_failed_or_unreached_submission:
                first_failed_or_unreached_submission = submission
        finally:
            submission.save()
    batchtype.cleanup(STUDENT_SOLUTION_DIR,MODEL_SOLUTION_DIR)
    if first_failed_or_unreached_submission is not None:
        # TODO: zou beter zijn hier een titel te voorzien, maar oké
        return (first_failed_or_unreached_submission.content_uid,analysis)
    else:
        return (submissions[-1].content_uid,[]) # empty analysis if everything is okay

@celery_app.task(priority=0)
def check_submission_batch(batchtype_id,repo_id,submission_ids,*args,**kwargs):
    # all id's have been queried by consumer, so assume they are okay
    # batchtype = strats.batch_types[batchtype_id]
    repo = Repo.objects.get(id=repo_id)
    subprocess.run(f'rm -rf {MODEL_SOLUTION_DIR}',shell=True)
    subprocess.run(f'rm -rf {STUDENT_SOLUTION_DIR}',shell=True)
    cmd = f'git clone {courses.courses[repo.course].solutions_url} {MODEL_SOLUTION_DIR}'
    print(courses.courses[repo.course].description)
    print(courses.courses[repo.course].solutions_url)
    print(cmd)
    subprocess.run(cmd,shell=True)
    subprocess.run(f'git clone {repo.url} {STUDENT_SOLUTION_DIR}',shell=True)
    subprocess.run(f'chmod -R 777 {STUDENT_SOLUTION_DIR}',shell=True)
    checksum = subprocess.run(f'cd {STUDENT_SOLUTION_DIR} ; git rev-parse HEAD',\
                              shell=True,\
                              capture_output=True).stdout.decode('utf-8').strip()
    submissions = [SubmissionV2.objects.get(id=submission_id) for submission_id in submission_ids]
    print('gaan over naar subtaak')
    if len(checksum) == 40:
        return _check_submissions_in_commit(submissions,checksum,batchtype_id)
    else:
        with transaction.atomic():
            for submission in submissions:
                submission.state = SubmissionState.NOT_REACHED
                submission.save()
        return ("geen oefening bereikt",[(None,None,None,"text",f"Probleem bij het ophalen van je repository. Klopt de URL en bevat de repository minstens één bestand?")])

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
        print(e)
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
