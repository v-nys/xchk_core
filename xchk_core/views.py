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
from .forms import CheckRequestFormSet, RepoSelectionForm, FeedbackForm
from .models import Repo, Submission, SubmissionState
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
    # from dependent to dependencies
    course = courses.courses()[course_title]
    # from dependency to dependents
    inverted_course = courses.invert_edges(course.structure)
    tocified = courses.tocify(course.structure,inverted_course)
    ul_representation = ulify(tocified,request,course_title)
    dependencies = {k.uid : [v.uid for v in vs] for (k,vs) in course.structure}
    return render(request,'xchk_core/course_overview.html',{'toc':ul_representation,'supplied_dependencies':dependencies})

def course_map_view(request,course_title):
    structure = courses.courses()[course_title].structure
    id_structure = [(dependent.uid,[dependency.uid for dependency in dependencies]) for (dependent, dependencies) in structure]
    # no need for json.dumps: template takes care of serialization as json-formatted string
    return render(request,'xchk_core/course_map.html',{'graph':id_structure})

def ulify(tocified,request,course_title,reverse_func=reverse):
    def _entry_to_li(e,expanded_nodes,user_submissions):
        classes = []
        # TODO: dit vraagt waarschijnlijk om héél veel database requests
        # alternatief
        # vraag eerst alle submissions van de user voor de cursus in kwestie, met state accepted
        # vraag dan alle submissions met state undecided als er nog geen entry accepted is
        # dus een of twee database queries
        # geef die info mee aan accepted_for / completed / is_accessible_by
        if e[0].accepted_for(request.user,user_submissions):
            classes.append('accepted')
        elif e[0].completed_by(request.user,user_submissions):
            classes.append('undecided')
        if not e[0].is_accessible_by(request.user,user_submissions):
            classes.append('locked')
        output = f'<li>'
        output += f'<a cv_uid="{e[0].uid}" href="{reverse_func(e[0].uid + "_view")}"'
        if classes:
            output += f' class="{" ".join([cls for cls in classes])}"'
        output += '>'
        output += f'{e[0].title}'
        output += '</a>'
        if not e[0].is_accessible_by(request.user,user_submissions):
            output += ' <i class="fas fa-lock"></i>'
        output += f' <i class="fas fa-crosshairs" for_cv_uid="{e[0].uid}"></i>'
        if e[0] not in expanded_nodes:
            output += f'<ul>{"".join([_entry_to_li(nested,expanded_nodes,user_submissions) for nested in e[1:]])}</ul>' if e[1:] else ''
        expanded_nodes.add(e[0])
        output += '</li>'
        return output
    # get all user submissions here to avoid hitting DB too hard
    # could restrict to accepted or undecided ones if performance is unsatisfactory
    user_submissions = Submission.objects.filter(submitter=request.user)
    expanded_nodes = set()
    return f'<ul>{"".join([_entry_to_li(entry,expanded_nodes,user_submissions) for entry in tocified])}</ul>'

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
    fields = ['course']
    success_url = reverse_lazy('checkerapp:index')

    # TODO: controleren dat cursus voorkomt als titel in courses.py
    # TODO: controleren dat user nog geen repo heeft voor deze cursus?
    def get_form(self, *args, **kwargs):
        form = super(CreateRepoView, self).get_form(*args,**kwargs)
        form.fields['course'] = ChoiceField(choices=[(key,key) for key in courses.courses().keys()])
        return form

    def form_valid(self, form):
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
        # response is json response
        form.instance.url = repo_response.json()['ssh_url']
        return super(CreateRepoView,self).form_valid(form)

class DeleteRepoView(LoginRequiredMixin,DeleteView):
    model = Repo
    success_url = reverse_lazy('checkerapp:index')

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.user != self.request.user and not self.request.user.is_superuser:
            return HttpResponseForbidden("Je mag geen repository verwijderen die aan iemand anders toebehoort.")
        return super(DeleteView,self).dispatch(request, *args, **kwargs)
