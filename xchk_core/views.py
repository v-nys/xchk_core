from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.generic.edit import CreateView
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
from .forms import CheckRequestFormSet, RepoSelectionForm, BatchTypeForm, FeedbackForm
from .models import Repo, SubmissionState
from . import courses
from django.forms import ChoiceField

@login_required
def submission_view(request,submission_pk):
    if request.user.is_superuser:
        return render(request,'checkerapp/submission.html',{'pk':submission_pk})
    else:
        return HttpResponseForbidden("Enkel beheerders mogen submissies bekijken")

@login_required
def new_course_view(request,course_title):
    course = courses.courses()[course_title]
    graph = courses.course_graphs()[course_title]
    for v in graph.vs:
        uid = v["contentview"].uid
        if uid != 'impossible_node':
            v["URL"] = reverse(f'{v["contentview"].uid}_view')
        else:
            v["URL"] = reverse(f'checkerapp:{v["contentview"].uid}_view')
    graph.write_dot(f'/tmp/{course_title}.gv')
    with open(f'/tmp/{course_title}.gv') as fh:
        dotfile = fh.read()
        print(dotfile)
        outpath = gv.render('dot','svg',f'/tmp/{course_title}.gv')
        with open(outpath) as fh2:
            return render(request,'checkerapp/course_overview2.html',{'graph':fh2.read()})

@login_required
def check_scripts_view(request):
    repos = Repo.objects.filter(user=request.user)
    nodes = Node.objects.all()
    if repos:
        batchtypeform = BatchTypeForm()
        repoform = RepoSelectionForm(owner=request.user)
        formset = CheckRequestFormSet(form_kwargs={'exercises': nodes, 'user': request.user})
        return render(request, 'checkerapp/index.html', {'batchtypeform': batchtypeform, 'repoform': repoform, 'formset': formset})
    else:
        return redirect('checkerapp:create_repo')

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
    def get_form(self, *args, **kwargs):
        form = super(CreateRepoView, self).get_form(*args,**kwargs)
        form.fields['course'] = ChoiceField(choices=[(key,key) for key in courses.courses().keys()])
        return form

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super(CreateRepoView,self).form_valid(form)
