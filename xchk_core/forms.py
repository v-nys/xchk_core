from django import forms
from .models import Repo, FeedbackTicket
from . import strats

class CheckRequestForm(forms.Form):

    def __init__(self, exercises, user, *args, **kwargs):
        super(CheckRequestForm,self).__init__(*args,**kwargs)
        numbered_exercises = [(node.pk,str(node)) for node in exercises] # if node.is_accessible_by(user)] uitgeschakeld zodat studenten Bruce alles kunnen checken
        self.fields['exercise'] = forms.ChoiceField(choices=numbered_exercises)

class FeedbackForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(FeedbackForm,self).__init__(*args,**kwargs)

    class Meta:
        model = FeedbackTicket
        fields = ['feedback_type', 'message']

class RepoSelectionForm(forms.ModelForm):

    def __init__(self, owner, uid, courses, *args, **kwargs):
        super().__init__(*args,**kwargs)
        candidate_repos = Repo.objects.filter(user=owner)
        final_candidate_repos = []
        for repo in candidate_repos:
            course = courses[repo.course]
            for (contentview,_) in course.structure:
                if contentview.uid == uid:
                    final_candidate_repos.append(repo)
                    break
        numbered_repos = [(repo.id,str(repo)) for repo in final_candidate_repos]
        self.fields['id'] = forms.ChoiceField(choices=numbered_repos)

    class Meta:
        model = Repo
        fields = ['id']

CheckRequestFormSet = forms.formset_factory(form=CheckRequestForm, max_num=15)
