import functools
import inspect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.http import HttpResponseServerError
from .forms import RepoSelectionForm
from . import strats, courses
from .models import SubmissionV2, SubmissionState
from .strats import *

class ContentView(View,LoginRequiredMixin):

    # FIXME: wil hier eigenlijk abstract class properties van maken, maar weet niet zeker hoe
    uid = 'aanvullen'
    strat = strats.Strategy()
    template = 'maaktnietuit.html'
    custom_data = {}
    title = 'aanvullen'

    @classmethod
    def is_accessible_by(cls,user):
        return user.is_superuser or any(cls.is_accessible_by_in(user,course) for course in courses.courses())

    @classmethod
    def is_accessible_by_in(cls,user,course):
        graph = courses.course_graphs()[course]
        for v in graphs.vs:
            print(v)
        try:
            v = graph.vs.find(label=cls.uid)
        except ValueError:
            return False
        preds = [e.source_vertex for e in graph.es.select(_to=v.index)]
        return all((p["contentview"].completed_by(user) for p in preds))

    @classmethod
    def completed_by(cls,user):
        submissions = SubmissionV2.objects.filter(content_uid=cls.uid).filter(submitter=user)
        return any((submission.state in [SubmissionState.ACCEPTED,SubmissionState.UNDECIDED] for submission in submissions))

    def get(self,request,*args,**kwargs):
        repoform = RepoSelectionForm(owner=request.user)
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
