from django import forms
from .models import Repo, FeedbackTicket
from . import checks
from . import strats

class CheckRequestForm(forms.Form):

    def __init__(self, exercises, user, *args, **kwargs):
        super(CheckRequestForm,self).__init__(*args,**kwargs)
        numbered_exercises = [(node.pk,str(node)) for node in exercises] # if node.is_accessible_by(user)] uitgeschakeld zodat studenten Bruce alles kunnen checken
        self.fields['exercise'] = forms.ChoiceField(choices=numbered_exercises)

class BatchTypeForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super(BatchTypeForm,self).__init__(*args,**kwargs)
        batch_types = [(idx,bt.description) for (idx,bt) in enumerate(strats.batch_types,0)]
        self.fields['batchtype'] = forms.ChoiceField(choices=batch_types)

class FeedbackForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(FeedbackForm,self).__init__(*args,**kwargs)

    class Meta:
        model = FeedbackTicket
        fields = ['feedback_type', 'message']

class RepoSelectionForm(forms.ModelForm):

    def __init__(self, owner, *args, **kwargs):
        containing_node = None
        if 'containing_node' in kwargs:
            print('containing_node is aanwezig')
            containing_node = kwargs['containing_node']
            del(kwargs['containing_node'])
        super(RepoSelectionForm,self).__init__(*args,**kwargs)
        candidate_repos = Repo.objects.filter(user=owner)
        if containing_node:
            print('extra filter op repos toegepast')
            candidate_repos = [repo for repo in candidate_repos if containing_node in repo.course.contained_nodes()]
        numbered_repos = [(repo.id,str(repo)) for repo in candidate_repos]
        self.fields['id'] = forms.ChoiceField(choices=numbered_repos)

    class Meta:
        model = Repo
        fields = ['id']

CheckRequestFormSet = forms.formset_factory(form=CheckRequestForm, max_num=15)
