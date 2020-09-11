import functools
import inspect
import iteration_utilities
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.http import HttpResponseServerError
from .forms import RepoSelectionForm
from . import strats, courses
from .models import Submission, SubmissionState
from .strats import *

class ContentView(View,LoginRequiredMixin):

    # FIXME: wil hier eigenlijk abstract class properties van maken, maar weet niet zeker hoe
    uid = 'aanvullen'
    strat = strats.Strategy()
    template = 'maaktnietuit.html'
    custom_data = {}
    title = 'aanvullen'

    @classmethod
    def is_accessible_by(cls,user,user_submissions=None):
        return user.is_superuser or any(cls.is_accessible_by_in(user,course,user_submissions) for course in courses.courses())

    @classmethod
    def is_accessible_by_in(cls,user,course,user_submissions=None):
        course_object = courses.courses()[course]
        structure = course_object.structure
        entry = iteration_utilities.first(structure,None,lambda x: x[0] is cls)
        if entry:
            return all((dependency.completed_by(user,user_submissions) for dependency in course_object.predecessors(cls)))
        else:
            return False

    @classmethod
    def completed_by(cls,user,user_submissions=None):
        if user_submissions is None:
            submissions = Submission.objects.filter(content_uid=cls.uid).filter(submitter=user)
        else:
            # if it is supplied, it should be a normal iterable
            submissions = filter(lambda x: x.content_uid == cls.uid, user_submissions)
        return any((submission.state in [SubmissionState.ACCEPTED,SubmissionState.UNDECIDED] for submission in submissions))

    @classmethod
    def accepted_for(cls,user,user_submissions=None):
        if user_submissions is None:
            submissions = Submission.objects.filter(content_uid=cls.uid).filter(submitter=user)
        else:
            submissions = filter(lambda x: x.content_uid == cls.uid, user_submissions)
        return any((submission.state == SubmissionState.ACCEPTED for submission in submissions))

    def get(self,request,*args,**kwargs):
        repoform = RepoSelectionForm(owner=request.user,uid=self.uid,courses=courses.courses())
        user = request.user
        if self.__class__.is_accessible_by(user):
            instructions = self.strat.instructions(self.uid)
            return render(request,self.template,{'pagetitle': self.title, 'uid':self.uid,'repoform':repoform,'instructions':instructions,'custom_data':self.custom_data})
        else:
            return HttpResponseServerError()

class ImpossibleNodeView(ContentView):

    uid = 'impossible_node'
    strat = strats.Strategy(refusing_check=strats.TrueCheck())
    template = 'checkerapp/impossible_node.html'

def is_content_view(e):
    return inspect.isclass(e) and issubclass(e,ContentView)

def all_contentviews():
    for cv in set(ContentView.__subclasses__()):
        yield cv
