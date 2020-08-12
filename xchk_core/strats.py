import logging
import os
from collections import namedtuple
from .models import SubmissionState

logger = logging.getLogger(__name__)

# TODO: consider merging into a single composite
OutcomeComponent = namedtuple('OutcomeComponent', ['component_number','outcome','desired_outcome','renderer','renderer_data'])
OutcomeAnalysis = namedtuple('OutcomeAnalysis', ['outcome','outcomes_components','successor_component_number'])
StratInstructions = namedtuple('StratInstructions', ['refusing','accepting'])

AT_LEAST_ONE_TEXT = "Aan minstens één van volgende voorwaarden is voldaan:"
ALL_OF_TEXT = "Aan al volgende voorwaarden is voldaan:"

class CheckingPredicate:

    def instructions(self,exercise_name):
        """Returns a hierarchical representation of the explicit conditions to be met for this check to return `True`."""
        return [f"True"]

    def negative_instructions(self,exercise_name):
        """Returns a hierarchical representation of the explicit conditions to be met for this check to return `False`."""
        return [f"False"]

    def component_checks(self):
        return []

    # TODO: deprecate?
    # component FileExistsChecks tell us this, so component_checks would be enough...
    def mentioned_files(self,exercise_name):
        """This is here so we can easily check submitted relevant files through UI."""
        return set()

    # alle properties moeten gelijk zijn en klasse moet gelijk zijn
    # overschrijven is nodig om `in` te gebruiken op ondersteunde checks batch type
    def __eq__(self,obj):
        same_types = type(self) == type(obj)
        same_vars = vars(self) == vars(obj)
        return same_types and same_vars

    def check_submission(self,submission,student_path,model_path,desired_outcome,init_check_number,parent_is_negation=False):
        """Returns an `OutcomeAnalysis` representing the global analysis of a submission.

        The `OutcomeAnalysis` represents outcome of a check, assuming the current check is top-level.
        It always has at least one component, which may contain more nested components."""
        components = [OutcomeComponent(component_number=init_check_number,
                                       outcome=True,
                                       desired_outcome=desired_outcome,
                                       renderer="text" if not desired_outcome else None,
                                       renderer_data="aan false kan nooit voldaan zijn" if not desired_outcome else None)]
        return OutcomeAnalysis(outcome=True,
                               outcomes_components=components,
                               successor_component_number=init_check_number+1)

class TrueCheck(CheckingPredicate):
    pass

class Negation(CheckingPredicate):

    def __init__(self,negated):
        self.negated_predicate = negated

    def negative_instructions(self,exercise_name):
        return self.negated_predicate.instructions(exercise_name)

    def instructions(self,exercise_name):
        return self.negated_predicate.negative_instructions(exercise_name)

    def component_checks(self):
        # negatie op zich mag altijd, hangt af van onderdelen...
        return self.negated_predicate.component_checks()

    def mentioned_files(self,exercise_name):
        return self.negated_predicate.mentioned_files(exercise_name)

    def check_submission(self,submission,student_path,model_path,desired_outcome,init_check_number,parent_is_negation=False):
        # cannot simply copy child analysis, because instructions are simplified through De Morgan
        # invert the desired outcome, but also invert the explanation in case of mismatch
        # for loose coupling, just tell child that parent is a negation
        child_analysis = self.negated_predicate.check_submission(submission,student_path,model_path,not desired_outcome,init_check_number,parent_is_negation=True)
        return OutcomeAnalysis(outcome=not child_analysis.outcome,
                               outcomes_components=child_analysis.outcomes_components, # there is no separate component for this check
                               successor_component_number=child_analysis.successor_component_number) # negation is absorbed into instruction

class ConjunctiveCheck(CheckingPredicate):

    def __init__(self,conjuncts):
        self.conjuncts = conjuncts

    def mentioned_files(self,exercise_name):
        return set([fn for conjunct in self.conjuncts for fn in conjunct.mentioned_files(exercise_name)])

    def instructions(self,exercise_name):
        subinstructions = []
        for conjunct in self.conjuncts:
            subinstructions.append(conjunct.instructions(exercise_name))
        return [ALL_OF_TEXT] + subinstructions

    def negative_instructions(self,exercise_name):
        subinstructions = []
        for conjunct in self.conjuncts:
            # note use of `negative_instructions`
            # De Morgan's law applied to conjunction
            subinstructions.append(conjunct.negative_instructions(exercise_name))
        return [AT_LEAST_ONE_TEXT] + subinstructions

    def component_checks(self):
        return [c for conjunct in self.conjuncts for c in conjunct.component_checks()]

    def check_submission(self,submission,student_path,model_path,desired_outcome,init_check_number,parent_is_negation=False):
        exit_code = True # assume
        next_check_number = init_check_number + 1
        analysis_children = []
        for conjunct in self.conjuncts:
            if exit_code:
                outcome_analysis_child = conjunct.check_submission(submission,student_path,model_path,desired_outcome,next_check_number)
                analysis_children += outcome_analysis_child.outcomes_components
                exit_code = exit_code and outcome_analysis_child.outcome
            else:
                # still need to do this due to short circuiting and numbering, but don't run check
                # could add non-SC variant later on...
                (_,next_check_number) = conjunct.instructions(submission.content_uid)
        error_msg = None
        if exit_code != desired_outcome:
            if not parent_is_negation:
                error_msg = f"AND moest {desired_outcome} leveren, leverde {exit_code}"
            else:
                error_msg = f"OR moest {not desired_outcome} leveren, leverde {not exit_code}"
        return OutcomeAnalysis(outcome=exit_code,components=[OutcomeComponent(component_number=init_check_number,outcome=exit_code,desired_outcome=desired_outcome,renderer="text" if exit_code != desired_outcome else None,renderer_data=error_msg)] + analysis_children,successor_component_number=next_check_number)

class FileExistsCheck(CheckingPredicate):

    def __init__(self,name=None,extension=None):
        self.name = name
        self.extension = extension

    def entry(self,exercise_name):
        return f'{self.name or exercise_name}{"." if self.extension else ""}{self.extension or ""}'

    def mentioned_files(self,exercise_name):
        return set(self.entry(exercise_name))

    def instructions(self,exercise_name):
        return [f'Je hebt een bestand met naam {self.entry(exercise_name)}']

    def negative_instructions(self,exercise_name):
        return [f'Je hebt geen bestand met naam {self.entry(exercise_name)}']

    def check_submission(self,submission,student_path,model_path,desired_outcome,init_check_number,parent_is_negation=False):
        exercise_name = submission.content_uid
        entry = self.entry(exercise_name)
        outcome = os.path.exists(os.path.join(student_path,self.entry(exercise_name)))
        if outcome and not desired_outcome:
            extra_info = f"{entry} mag niet bestaan en bestaat toch"
        elif not outcome and desired_outcome:
            extra_info = f"{entry} moet bestaan, maar bestaat niet"
        else:
            extra_info = None
        components = [OutcomeComponent(component_number=init_check_number,
                                       outcome=outcome,
                                       desired_outcome=desired_outcome,
                                       renderer=None if outcome == desired_outcome else "text",
                                       renderer_data=extra_info)]
        return OutcomeAnalysis(outcome=outcome,outcomes_components=components,successor_component_number=init_check_number+1)

class DisjunctiveCheck(CheckingPredicate):

    def __init__(self,disjuncts):
        self.disjuncts = disjuncts

    def mentioned_files(self,exercise_name):
        return set([fn for disjunct in self.disjuncts for fn in disjunct.mentioned_files(exercise_name)])

    def instructions(self,exercise_name):
        subinstructions = []
        for disjunct in self.disjuncts:
            subinstructions.append(disjunct.instructions(exercise_name))
        return [AT_LEAST_ONE_TEXT] + subinstructions

    def negative_instructions(self,exercise_name):
        subinstructions = []
        for disjunct in self.disjuncts:
            # note use of `negative_instructions`
            # De Morgan's law applied to disjunction
            subinstructions.append(disjunct.negative_instructions(exercise_name))
        return [ALL_OF_TEXT] + subinstructions

    def component_checks(self):
        return [c for disjunct in self.disjuncts for c in disjunct.component_checks()]

    def check_submission(self,submission,student_path,model_path,desired_outcome,init_check_number,parent_is_negation=False):
        exit_code = False # assume
        next_check_number = init_check_number + 1
        analysis_children = []
        for disjunct in self.disjuncts:
            if not exit_code:
                outcome_analysis_child = disjunct.check_submission(submission,student_path,model_path,desired_outcome,next_check_number)
                analysis_children += outcome_analysis_child.outcomes_components
                exit_code = exit_code or outcome_analysis_child.outcome
            else:
                # still need to do this due to short circuiting and numbering, but don't run check
                # could add non-SC variant later on...
                # TODO: hier verder zoeken
                # normaal bevat een OutcomeAnalysis de successor_component_number
                # wat is daar het effect van op heel dit?
                # ook: wat met conjunctieve checks?
                # vermoedelijk mag de else tak gewoon weg, maar moet nog in kaart brengen...
                (_,next_check_number) = disjunct.instructions(submission.content_uid,next_check_number)
        error_msg = None
        if exit_code != desired_outcome:
            if not parent_is_negation:
                error_msg = f"OR moest {desired_outcome} leveren, leverde {exit_code}"
            else:
                error_msg = f"AND moest {not desired_outcome} leveren, leverde {not exit_code}"
        return OutcomeAnalysis(outcome=exit_code,outcomes_components=[OutcomeComponent(component_number=init_check_number,outcome=exit_code,desired_outcome=desired_outcome,renderer="text" if exit_code != desired_outcome else None,renderer_data=error_msg)] + analysis_children,successor_component_number=next_check_number)

class Strategy:

    def __init__(self,refusing_check=Negation(TrueCheck()),accepting_check=Negation(TrueCheck())):
        self.refusing_check = refusing_check
        self.accepting_check = accepting_check

    def mentioned_files(self,exercise_name):
        return self.refusing_check.mentioned_files(exercise_name).union(self.accepting_check.mentioned_files(exercise_name))

    def component_checks(self):
        return self.refusing_check.component_checks() + self.accepting_check.component_checks()

    def instructions(self,exercise_name):
        ref_instructions = self.refusing_check.instructions(exercise_name)
        acc_instructions = self.accepting_check.instructions(exercise_name)
        return StratInstructions(
                refusing=ref_instructions,
                accepting=acc_instructions)
 
    def check_submission(self,submission,student_path,model_path):
        (outcome_refusing,analysis_refusing) = (None,[])
        (outcome_accepting,analysis_accepting) = (None,[])
        try:
            outcome_analysis_refusing = self.refusing_check.check_submission(submission,student_path,model_path,desired_outcome=False,init_check_number=1)
            if outcome_analysis_refusing.outcome:
                return (SubmissionState.NEW_REFUSED,outcome_analysis_refusing.outcomes_components)
            outcome_analysis_accepting = self.accepting_check.check_submission(submission,student_path,model_path,desired_outcome=True,init_check_number=outcome_analysis_refusing.successor_component_number)
            if outcome_accepting:
                return (SubmissionState.ACCEPTED,outcome_analysis_accepting.outcomes_components)
        except Exception as e:
            logger.exception('Fout bij controle submissie: %s',e)
        logger.warning(f'Submissie die niet beslist kon worden. Outcome refusing was {outcome_refusing} en outcome accepting was {outcome_accepting}')
        return (SubmissionState.PENDING,[OutcomeComponent(component_number=None,outcome=None,desired_outcome=None,renderer="text",renderer_data=f"Het systeem kan niet automatisch bepalen of je inzending klopt. De lector wordt verwittigd. Weigering was {outcome_analysis_refusing.outcome} en aanvaarding was {outcome_analysis_accepting.outcome}")] + outcome_analysis_refusing.components + outcome_analysis_accepting.components)
