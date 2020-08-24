from django.shortcuts import render, redirect
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.views.generic.edit import CreateView, DeleteView
from django.views.generic.detail import DetailView
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy, reverse
from django.http import HttpResponse, HttpResponseForbidden
from django.contrib import messages
import datetime
import re
import requests
import itertools
import graphviz as gv
from .forms import CheckRequestFormSet, RepoSelectionForm, FeedbackForm
from .models import Repo, SubmissionState
from . import courses
from django.forms import ChoiceField
from django.conf import settings
import requests
import json

def index_view(request):
    return render(request,'xchk_core/index.html')

def test_gitea_view(request):
    # using HTTP here!
    # test: maakt een repo aan
    url = f'http://gitea:3000/api/v1/admin/users/{request.user.username}/repos'
    data = {'auto_init': True,
            'default_branch': 'master',
            'description': 'repo for xchk',
            'name': 'my_first_repo',
            'private': True}
    headers = {'accept': 'application/json', 'Content-Type': 'application/json', 'Authorization': f'token {settings.GITEA_APPLICATION_TOKEN}'}
    response = requests.post(url, data=json.dumps(data), headers=headers)
    return render(request, 'checkerapp/gitea_test_result.html',{'response':response})

@login_required
def submission_view(request,submission_pk):
    if request.user.is_superuser:
        return render(request,'checkerapp/submission.html',{'pk':submission_pk})
    else:
        return HttpResponseForbidden("Enkel beheerders mogen submissies bekijken")

@login_required
def new_course_view(request,course_title):
    repo = None
    try:
        repo = Repo.objects.filter(user=request.user).get(course=course_title)
    except ObjectDoesNotExist as e:
        if not request.user.is_superuser:
            raise e
    course = courses.courses()[course_title]
    graph = courses.course_graphs()[course_title]
    for v in graph.vs:
        uid = v["contentview"].uid
        if uid != 'impossible_node':
            # TODO: code generates excessive number of queries
            if v["contentview"].is_accessible_by(request.user):
                v["URL"] = reverse(f'{v["contentview"].uid}_view')
                v["color"] = "black"
                v["fontcolor"] = "black"
                if v["contentview"].accepted_for(request.user):
                    v["color"] = "green"
                    v["fontcolor"] = "green"
                elif v["contentview"].completed_by(request.user):
                    v["color"] = "orange"
                    v["fontcolor"] = "orange"
            else:
               v["color"] = "gray"
               v["fontcolor"] = "gray"
    graph.write_dot(f'/tmp/{course_title}.gv')
    with open(f'/tmp/{course_title}.gv') as fh:
        dotfile = fh.read()
        outpath = gv.render('dot','svg',f'/tmp/{course_title}.gv')
        with open(outpath) as fh2:
            # igraph always numbers vertices
            # so we have to get dependencies from graph, not course
            dependencies = {str(v.index) : [str(e.source) for e in graph.es.select(_target=v)] for v in graph.vs}
            data = {'graph':fh2.read(), 'supplied_dependencies': dependencies}
            if repo:
                data['repo_id'] = repo.id
            return render(request,'xchk_core/course_overview.html',data)

def node_feedback_view(request,node_pk):
    form = FeedbackForm(request.POST)
    if form.is_valid():
        ticket = form.instance
        ticket.sender = request.user
        ticket.node = Node.objects.get(pk=node_pk)
        ticket.timestamp = datetime.datetime.now()
        ticket.save()
        messages.success(request, "Je feedback is geregistreerd. Bedankt!")
    else:
        messages.error(request, "Je feedback bevatte ongeldige data.")
    return redirect('checkerapp:node_view',node_pk)

def course_feedback_view(request,course_pk):
    form = FeedbackForm(request.POST)
    if form.is_valid():
        ticket = form.instance
        ticket.sender = request.user
        ticket.course = Course.objects.get(pk=course_pk)
        ticket.timestamp = datetime.datetime.now()
        ticket.save()
        messages.success(request, "Je feedback is geregistreerd. Bedankt!")
    else:
        messages.error(request, "Je feedback bevatte ongeldige data.")
    return redirect('checkerapp:course_view',course_pk)

class CreateRepoView(LoginRequiredMixin,CreateView):
    model = Repo
    fields = ['course','url']
    success_url = reverse_lazy('checkerapp:index')

    # TODO: controleren dat cursus voorkomt als titel in courses.py
    # TODO: controleren dat user nog geen repo heeft voor deze cursus?
    def get_form(self, *args, **kwargs):
        form = super(CreateRepoView, self).get_form(*args,**kwargs)
        form.fields['course'] = ChoiceField(choices=[(key,key) for key in courses.courses().keys()])
        return form

    def form_valid(self, form):
        # TODO: admin collaborator maken van deze repo
        form.instance.user = self.request.user
        url = f'http://gitea:3000/api/v1/admin/users/{self.request.user.username}/repos'
        data = {'auto_init': True,
                'default_branch': 'master',
                'description': f'repo for {form.instance.course} xchk course',
                'name': f'{form.instance.course}',
                'private': True}
        headers = {'accept': 'application/json', 'Content-Type': 'application/json', 'Authorization': f'token {settings.GITEA_APPLICATION_TOKEN}'}
        repo_response = requests.post(url, data=json.dumps(data), headers=headers)
        url = f'http://gitea:3000/api/v1/repos/{self.request.user.username}/{form.instance.course}/collaborators/vincent'
        data = {'permission': 'admin'}
        collab_response = requests.put(url, data=json.dumps(data), headers=headers)
        return super(CreateRepoView,self).form_valid(form)

class DeleteRepoView(LoginRequiredMixin,DeleteView):
    model = Repo
    success_url = reverse_lazy('checkerapp:index')

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.user != self.request.user and not self.request.user.is_superuser:
            return HttpResponseForbidden("Je mag geen repository verwijderen die aan iemand anders toebehoort.")
        return super(DeleteView,self).dispatch(request, *args, **kwargs)
