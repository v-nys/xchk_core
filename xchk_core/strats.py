import logging
import os
from collections import namedtuple
from iteration_utilities import deepflatten
from .models import SubmissionState

logger = logging.getLogger(__name__)

# TODO: consider merging into a single composite
# outcome is present in OutcomeComponent anyway, so just make one Outcome tuple?
OutcomeComponent = namedtuple('OutcomeComponent', ['component_number','outcome','desired_outcome','rendered_data','acceptable_to_ancestor'])
OutcomeAnalysis = namedtuple('OutcomeAnalysis', ['outcome','outcomes_components'])
StrategyAnalysis = namedtuple('StrategyAnalysis', ['submission_state','submission_url','submission_checksum'])
StratInstructions = namedtuple('StratInstructions', ['refusing','accepting'])

AT_LEAST_ONE_TEXT = "Aan minstens één van volgende voorwaarden is voldaan:"
ALL_OF_TEXT = "Aan al volgende voorwaarden is voldaan:"

class CheckingPredicate:

    @property
    def number_of_instructions(self):
        """Get the number of instructions in a checking predicate."""
        return len(list(deepflatten(self.instructions("bla"),ignore=str)))

    def instructions(self,exercise_name):
        """Returns a hierarchical representation of the explicit conditions to be met for this check to return `True`.

        This is a list representation of a tree.
        The first element of a list represents a node; subsequent elements represent child trees.
        If these subsequent elements are not lists, they are leaves of the first element.
        Note that `exercise_name` cannot affect the shape of this tree.

        The shape of this tree must be identical to that returned by `negative_instructions`."""
        return [f"True"]

    def negative_instructions(self,exercise_name):
        """Returns a hierarchical representation of the explicit conditions to be met for this check to return `False`.

        This is a list representation of a tree.
        The first element of a list represents a node; subsequent elements represent child trees.
        If these subsequent elements are not lists, they are leaves of the first element.
        Note that `exercise_name` cannot affect the shape of this tree.

        The shape of this tree must be identical to that returned by `instructions`."""
        return [f"False"]

    def component_checks(self):
        return []

    # alle properties moeten gelijk zijn en klasse moet gelijk zijn
    # overschrijven is nodig om `in` te gebruiken op ondersteunde checks batch type
    def __eq__(self,obj):
        same_types = type(self) == type(obj)
        same_vars = vars(self) == vars(obj)
        return same_types and same_vars

    def check_submission(self,submission,student_path,desired_outcome,init_check_number,ancestor_has_alternatives,parent_is_negation=False,open=open):
        """Returns an `OutcomeAnalysis` representing the global analysis of a submission.

        The `OutcomeAnalysis` represents outcome of a check, assuming the current check is top-level.
        It always has at least one component, which may contain more nested components."""
        components = [OutcomeComponent(component_number=init_check_number,
                                       outcome=True,
                                       desired_outcome=desired_outcome,
                                       rendered_data=f"<p>Aan de gewenste uitkomst, <code>false</code>, kan nooit voldaan zijn.</p>" if not desired_outcome else None,
                                       acceptable_to_ancestor=desired_outcome or ancestor_has_alternatives)]
        return OutcomeAnalysis(outcome=True,
                               outcomes_components=components)

class TrueCheck(CheckingPredicate):
    pass

FalseCheck = lambda: Negation(TrueCheck())

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

    def check_submission(self,submission,student_path,desired_outcome,init_check_number,ancestor_has_alternatives,parent_is_negation=False,open=open):
        # cannot simply copy child analysis, because instructions are simplified through De Morgan
        # invert the desired outcome, but also invert the explanation in case of mismatch
        # for loose coupling, just tell child that parent is a negation
        # double negation is simplified away by inverting parent_is_negation rather than setting to True
        child_analysis = self.negated_predicate.check_submission(submission,student_path,not desired_outcome,init_check_number,ancestor_has_alternatives,parent_is_negation=not parent_is_negation,open=open)
        return OutcomeAnalysis(outcome=not child_analysis.outcome,
                               outcomes_components=child_analysis.outcomes_components)

class ConjunctiveCheck(CheckingPredicate):

    def __init__(self,conjuncts):
        self.conjuncts = conjuncts

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

    def check_submission(self,submission,student_path,desired_outcome,init_check_number,ancestor_has_alternatives,parent_is_negation=False,open=open):
        exit_code = True # assume
        next_check_number = init_check_number + 1
        analysis_children = []
        child_value_ancestor_has_alternatives = ancestor_has_alternatives
        if len(self.conjuncts) > 1 and not desired_outcome and not parent_is_negation:
            child_value_ancestor_has_alternatives = True
        for conjunct in self.conjuncts:
            if exit_code:
                outcome_analysis_child = conjunct.check_submission(submission,student_path,desired_outcome,next_check_number,child_value_ancestor_has_alternatives,open=open)
                next_check_number += conjunct.number_of_instructions
                analysis_children += outcome_analysis_child.outcomes_components
                exit_code = exit_code and outcome_analysis_child.outcome
        error_msg = None
        if exit_code != desired_outcome:
            if not parent_is_negation:
                error_msg = f"Deze voorwaarde is een AND van alle instructies die er onder staan. AND moest {desired_outcome} leveren, leverde {exit_code}"
            else:
                error_msg = f"OR moest {not desired_outcome} leveren, leverde {not exit_code}"
        return OutcomeAnalysis(outcome=exit_code,outcomes_components=[OutcomeComponent(component_number=init_check_number,outcome=exit_code,desired_outcome=desired_outcome,rendered_data=f"<p>{error_msg}</p>" if exit_code != desired_outcome else None,acceptable_to_ancestor=exit_code == desired_outcome or ancestor_has_alternatives)] + analysis_children)

class FileExistsCheck(CheckingPredicate):

    def __init__(self,name=None,extension=None):
        self.name = name
        self.extension = extension

    def entry(self,exercise_name):
        return f'{self.name or exercise_name}{"." if self.extension else ""}{self.extension or ""}'

    def instructions(self,exercise_name):
        return [f'Je hebt een bestand met naam {self.entry(exercise_name)}']

    def negative_instructions(self,exercise_name):
        return [f'Je hebt geen bestand met naam {self.entry(exercise_name)}']

    def check_submission(self,submission,student_path,desired_outcome,init_check_number,ancestor_has_alternatives,parent_is_negation=False,open=open):
        exercise_name = submission.content_uid
        entry = self.entry(exercise_name)
        outcome = os.path.exists(os.path.join(student_path,self.entry(exercise_name)))
        if outcome and not desired_outcome:
            extra_info = f"{entry} bestaat"
        elif not outcome and desired_outcome:
            extra_info = f"""<p><code>{entry}</code> bestaat niet. Als je toch een bestand met deze naam op de juiste locatie op jouw machine ziet, let er dan op dat de bestandsextensie deel uitmaakt van de bestandsnaam. Zorg eerst dat bestandsextensies getoond worden. <a href='https://sawtoothsoftware.com/resources/knowledge-base/general-issues/how-to-show-file-name-extensions-in-windows-explorer'>Hier</a> staat hoe je dat kan doen onder Windows. <a href='https://www.techradar.com/how-to/computing/apple/how-to-show-or-hide-file-extensions-in-mac-os-x-1295830'>Hier</a> staat hoe je dat kan doen onder Mac OS.</p>
            <p>Kopieer, wanneer bestandsextensies getoond worden, de gevraagde bestandsnaam en plak die over de naam van het bestand dat je al hebt. Dit kan ook moeilijk te spotten typfouten voorkomen.</p>

            <p>Je kan je geüploade bestanden terugvinden op <a href="gitea.xchk.be">gitea.xchk.be</a>. Om hier de eerste keer in te loggen, gebruik je het wachtwoord dat je terugvindt op je profielpagina.</p>"""
        else:
            extra_info = None
        components = [OutcomeComponent(component_number=init_check_number,
                                       outcome=outcome,
                                       desired_outcome=desired_outcome,
                                       rendered_data=f"{extra_info}" if outcome != desired_outcome else "",
                                       acceptable_to_ancestor=outcome == desired_outcome or ancestor_has_alternatives)]
        return OutcomeAnalysis(outcome=outcome,outcomes_components=components)

class DisjunctiveCheck(CheckingPredicate):

    def __init__(self,disjuncts):
        self.disjuncts = disjuncts

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

    def check_submission(self,submission,student_path,desired_outcome,init_check_number,ancestor_has_alternatives,parent_is_negation=False,open=open):
        exit_code = False # assume
        next_check_number = init_check_number + 1
        analysis_children = []
        child_value_ancestor_has_alternatives = ancestor_has_alternatives
        if len(self.disjuncts) > 1 and desired_outcome and not parent_is_negation:
            child_value_ancestor_has_alternatives = True
        for disjunct in self.disjuncts:
            if not exit_code:
                # has successor_component_number field
                outcome_analysis_child = disjunct.check_submission(submission,student_path,desired_outcome,next_check_number,child_value_ancestor_has_alternatives,open=open)
                next_check_number += disjunct.number_of_instructions
                analysis_children += outcome_analysis_child.outcomes_components
                exit_code = exit_code or outcome_analysis_child.outcome
        error_msg = None
        if exit_code != desired_outcome:
            if not parent_is_negation:
                error_msg = f"OR moest {desired_outcome} leveren, leverde {exit_code}"
            else:
                error_msg = f"AND moest {not desired_outcome} leveren, leverde {not exit_code}"
        return OutcomeAnalysis(outcome=exit_code,outcomes_components=[OutcomeComponent(component_number=init_check_number,outcome=exit_code,desired_outcome=desired_outcome,rendered_data=f"<p>{error_msg}</p>",acceptable_to_ancestor=exit_code == desired_outcome or ancestor_has_alternatives)] + analysis_children)

class Strategy:

    def __init__(self,refusing_check=Negation(TrueCheck()),accepting_check=Negation(TrueCheck())):
        self.refusing_check = refusing_check
        self.accepting_check = accepting_check

    def component_checks(self):
        return self.refusing_check.component_checks() + self.accepting_check.component_checks()

    def instructions(self,exercise_name):
        ref_instructions = self.refusing_check.instructions(exercise_name)
        acc_instructions = self.accepting_check.instructions(exercise_name)
        return StratInstructions(
                refusing=ref_instructions,
                accepting=acc_instructions)
 
    def check_submission(self,submission,student_path):
        (outcome_refusing,analysis_refusing) = (None,[])
        (outcome_accepting,analysis_accepting) = (None,[])
        general_error_analysis = (StrategyAnalysis(submission_state=SubmissionState.NOT_REACHED,submission_url=submission.repo.url,submission_checksum=submission.checksum),[])
        if len(submission.checksum) != 40:
            return general_error_analysis
        try:
            outcome_analysis_refusing = self.refusing_check.check_submission(submission,student_path,desired_outcome=False,init_check_number=1,ancestor_has_alternatives=False)
            if outcome_analysis_refusing.outcome:
                return (StrategyAnalysis(submission_state=SubmissionState.REFUSED,submission_url=submission.repo.url,submission_checksum=submission.checksum),outcome_analysis_refusing.outcomes_components)
            outcome_analysis_accepting = self.accepting_check.check_submission(submission,student_path,desired_outcome=True,init_check_number=outcome_analysis_refusing.outcomes_components[-1].component_number+1,ancestor_has_alternatives=False)
            if outcome_analysis_accepting.outcome:
                return (StrategyAnalysis(submission_state=SubmissionState.ACCEPTED,submission_url=submission.repo.url,submission_checksum=submission.checksum),outcome_analysis_accepting.outcomes_components)
        except Exception as e:
            logger.exception('Fout bij controle submissie: %s',e)
            return general_error_analysis
        return (StrategyAnalysis(submission_state=SubmissionState.UNDECIDED,submission_url=submission.repo.url,submission_checksum=submission.checksum),outcome_analysis_refusing.outcomes_components + outcome_analysis_accepting.outcomes_components)
