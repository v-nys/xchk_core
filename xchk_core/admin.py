from django import forms
from django.contrib import admin
from .models import Repo, FeedbackTicket, Submission

class RepoForm(forms.ModelForm):
    class Meta:
        model = Repo
        exclude = []

class RepoAdmin(admin.ModelAdmin):
    form = RepoForm
    list_filter = ('course','user__username')

class SubmissionAdmin(admin.ModelAdmin):
    list_filter = ('state','exercise','submitter__username','timestamp')

class FeedbackTicketAdmin(admin.ModelAdmin):
    list_filter = ('feedback_type',)

admin.site.register(Submission)
admin.site.register(Repo, RepoAdmin)
admin.site.register(FeedbackTicket,FeedbackTicketAdmin)
