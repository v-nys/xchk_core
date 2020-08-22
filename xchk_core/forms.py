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

    def __init__(self, owner, *args, **kwargs):
        print(kwargs.get('uid','uid is niet toegankelijk op deze manier'))
        super(RepoSelectionForm,self).__init__(*args,**kwargs)
        # FIXME
        # niet gewoon alles repos van deze user
        # willen repos waarvoor cursus node in kwestie bevat
        # denk dat containing_node er niet is...?
        # repo.course.... kan al niet meer: is gewoon CharField
        # dus containing_node zal ontbreken
        # er is wel hidden input uid
        # Course is geen model, maar kan wel opgevraagd worden via courses.courses()
        # elke Course heeft een veld structure
        # en dat is een lijst van tuples (view, dependencies)
        candidate_repos = Repo.objects.filter(user=owner)
        # if containing_node:
        #     candidate_repos = [repo for repo in candidate_repos]# if containing_node in repo.course.contained_nodes()]
        numbered_repos = [(repo.id,str(repo)) for repo in candidate_repos]
        self.fields['id'] = forms.ChoiceField(choices=numbered_repos)

    class Meta:
        model = Repo
        fields = ['id']

CheckRequestFormSet = forms.formset_factory(form=CheckRequestForm, max_num=15)
