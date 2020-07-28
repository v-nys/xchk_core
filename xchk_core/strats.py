from .models import SubmissionState
import logging
import os
from antlr4 import *
from .MultipleChoiceLexer import MultipleChoiceLexer
from .MultipleChoiceParser import MultipleChoiceParser
from .MultipleChoiceChecker import MultipleChoiceChecker

logger = logging.getLogger(__name__)

class CheckingPredicate:

    """Intended to be overwritten in subclasses. Default checking strategy always accepts so has no instructions."""
    def instructions(self,exercise_name,init_check_number):
        return ([f"True"], init_check_number + 1)

    def negative_instructions(self,exercise_name,init_check_number):
        return ([f"False"], init_check_number + 1)

    def component_checks(self):
        return []

    """This is here so we can easily check submitted relevant files through UI."""
    def mentioned_files(self,exercise_name):
        return set()

    # alle properties moeten gelijk zijn en klasse moet gelijk zijn
    # overschrijven is nodig om `in` te gebruiken op ondersteunde checks batch type
    def __eq__(self,obj):
        same_types = type(self) == type(obj)
        same_vars = vars(self) == vars(obj)
        return same_types and same_vars

    def check_submission(self,submission,student_path,model_path,desired_outcome,init_check_number,parent_is_negation=False):
        # TODO: aanpassen
        # overall outcome zal altijd True zijn voor nulvoorwaarde
        return ((True,\
                # houden tel bij van welke voorwaarde faalt om zo feedback op juiste vwd. te geven
                 [(init_check_number,\
                # verkregen uitkomst, makkelijk deze te hebben om info te filteren
                   True,\
                # moeten weten of deze juist wel of niet moest slagen
                   desired_outcome,\
                # renderer voor extra info
                   "text" if not desired_outcome else None,\
                # extra info in rendererformaat
                   "aan false kan nooit voldaan zijn" if not desired_outcome else None)]),\
                init_check_number + 1)

class TrueCheck(CheckingPredicate):
    pass

class Negation(CheckingPredicate):

    def __init__(self,negated):
        self.negated_predicate = negated

    def negative_instructions(self,exercise_name,init_check_number):
        return self.negated_predicate.instructions(exercise_name,init_check_number)

    def instructions(self,exercise_name,init_check_number):
        return self.negated_predicate.negative_instructions(exercise_name,init_check_number)

    def component_checks(self):
        # negatie op zich mag altijd, hangt af van onderdelen...
        return self.negated_predicate.component_checks()

    def mentioned_files(self,exercise_name):
        return self.negated_predicate.mentioned_files(exercise_name)

    def check_submission(self,submission,student_path,model_path,desired_outcome,init_check_number,parent_is_negation=False):
        # cannot simply copy child analysis, because instructions are simplified through De Morgan
        # invert the desired outcome, but also invert the explanation in case of mismatch
        # for loose coupling, just tell child that parent is a negation
        ((child_overall,child_analysis),child_next_check_number) = self.negated_predicate.check_submission(submission,student_path,model_path,not desired_outcome,init_check_number,parent_is_negation=True)
        return ((not child_overall,child_analysis),child_next_check_number)

class ConjunctiveCheck(CheckingPredicate):

    def __init__(self,conjuncts):
        self.conjuncts = conjuncts

    def mentioned_files(self,exercise_name):
        return set([fn for conjunct in self.conjuncts for fn in conjunct.mentioned_files(exercise_name)])

    def instructions(self,exercise_name,init_check_number):
        subinstructions = []
        next_init_check_number = init_check_number + 1
        for conjunct in self.conjuncts:
            (subinstruction_info,next_init_check_number) = conjunct.instructions(exercise_name,next_init_check_number)
            subinstructions.append(subinstruction_info)
        return (["Aan al volgende voorwaarden is voldaan:"] + subinstructions,next_init_check_number)

    def negative_instructions(self,exercise_name,init_check_number):
        subinstructions = []
        next_init_check_number = init_check_number + 1
        for conjunct in self.conjuncts:
            # note use of `negative_instructions`
            # De Morgan's law applied to conjunction
            (subinstruction_info,next_init_check_number) = conjunct.negative_instructions(exercise_name,next_init_check_number)
            subinstructions.append(subinstruction_info)
        return (['Aan minstens één van volgende voorwaarden is voldaan:'] + subinstructions,next_init_check_number)

    def component_checks(self):
        return [c for conjunct in self.conjuncts for c in conjunct.component_checks()]

    def check_submission(self,submission,student_path,model_path,desired_outcome,init_check_number,parent_is_negation=False):
        exit_code = True # assume
        # positions = ConjunctiveCheckConjunctPosition.objects.filter(conjunction=self).order_by('order')
        next_check_number = init_check_number + 1
        analysis_children = []
        for conjunct in self.conjuncts:
            if exit_code:
                ((child_result,child_analysis), next_check_number) = conjunct.check_submission(submission,student_path,model_path,desired_outcome,next_check_number)
                analysis_children += child_analysis
                exit_code = exit_code and child_result
            else:
                # still need to do this due to short circuiting and numbering, but don't run check
                # could add non-SC variant later on...
                (_,next_check_number) = conjunct.instructions(submission.content_uid,next_check_number)
        error_msg = None
        if exit_code != desired_outcome:
            if not parent_is_negation:
                error_msg = f"AND moest {desired_outcome} leveren, leverde {exit_code}"
            else:
                error_msg = f"OR moest {not desired_outcome} leveren, leverde {not exit_code}"
        return ((exit_code,\
                 [(init_check_number,exit_code,desired_outcome,"text" if exit_code != desired_outcome else None,error_msg)] + analysis_children),
                next_check_number)

class FileExistsCheck(CheckingPredicate):

    def __init__(self,name=None,extension=None):
        self.name = name
        self.extension = extension

    def entry(self,exercise_name):
        return f'{self.name or exercise_name}{"." if self.extension else ""}{self.extension or ""}'

    def mentioned_files(self,exercise_name):
        return set(self.entry(exercise_name))

    def instructions(self,exercise_name,init_check_number):
        return ([f'Je hebt een bestand met naam {self.entry(exercise_name)}'],init_check_number + 1)

    def negative_instructions(self,exercise_name,init_check_number):
        return ([f'Je hebt geen bestand met naam {self.entry(exercise_name)}'],init_check_number + 1)

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
        return ((outcome,\
                 [(init_check_number,\
                   outcome,\
                   desired_outcome,\
                   # geen renderer als alles zoals verwacht is
                   None if outcome == desired_outcome else "text",\
                   extra_info)]),\
                init_check_number + 1)

class MultipleChoiceFormatCheck(CheckingPredicate):

    def mentioned_files(self,exercise_name):
        return set(exercise_name + '.mc')

    def instructions(self,exercise_name,init_check_number):
        # TODO: moet hier links,... kunnen invoegen...
        return ([f'Je multiple choice bestand volgt <HET AFGESPROKEN FORMAAT>.'],init_check_number + 1)

    def negative_instructions(self,exercise_name,init_check_number):
        return ([f'Je multiple choice bestand volgt <HET AFGESPROKEN FORMAAT> niet.'],init_check_number + 1)

    def check_submission(self,submission,student_path,model_path,desired_outcome,init_check_number,parent_is_negation=False):
        # TODO: is dit de geschikte plaats voor exception handling of niet?
        # hier moeten we ja/nee zeggen en de relatie tot gewenste uitkomst geven
        # is niet duidelijk bij gelijk welke exception, dus beter niveau hoger afhandelen?
        input_stream = FileStream(os.path.join(student_path,f'{submission.content_uid}.mc'))
        lexer = MultipleChoiceLexer(input_stream)
        stream = CommonTokenStream(lexer)
        parser = MultipleChoiceParser(stream)
        tree = parser.multiplechoice()
        outcome = parser.getNumberOfSyntaxErrors() == 0
        if outcome and not desired_outcome:
            extra_info = f"Je multiple choice bestand volgt het afgesproken formaat en dat mag niet"
        elif not outcome and desired_outcome:
            extra_info = f"Je multiple choice bestand volgt het afgesproken formaat niet en dat moet juist wel"
        else:
            extra_info = None
        return ((outcome,\
                 [(init_check_number,\
                   outcome,\
                   desired_outcome,\
                   # geen renderer als alles zoals verwacht is
                   None if outcome == desired_outcome else "text",\
                   extra_info)]),\
                init_check_number + 1)

class MultipleChoiceAnswerCheck(CheckingPredicate):

    def __init__(self,mc_data):
        self.mc_data = mc_data

    def mentioned_files(self,exercise_name):
        return set(exercise_name + '.mc')

    def instructions(self,exercise_name,init_check_number):
        return ([f'Je hebt alle correcte antwoorden per vraag aangeduid.'],init_check_number + 1)

    def negative_instructions(self,exercise_name,init_check_number):
        return ([f'Je hebt niet alle correcte antwoorden per vraag aangeduid.'],init_check_number + 1)

    def check_submission(self,submission,student_path,model_path,desired_outcome,init_check_number,parent_is_negation=False):
        # TODO: in veronderstelling dat parsen lukt -> listener (of visitor) voorzien van de mc_data
        # TODO: is dit de geschikte plaats voor exception handling of niet?
        # moet bij elke vraag nummer controleren (moet volgen op vorig, dat begint bij 0)
        # moet bij elke vraag controleren of de antwoorden (na lower case) voorkomen in de reeks antwoorden
        # hier moeten we ja/nee zeggen en de relatie tot gewenste uitkomst geven
        # is niet duidelijk bij gelijk welke exception, dus beter niveau hoger afhandelen?
        input_stream = FileStream(os.path.join(student_path,f'{submission.content_uid}.mc'))
        lexer = MultipleChoiceLexer(input_stream)
        stream = CommonTokenStream(lexer)
        parser = MultipleChoiceParser(stream)
        tree = parser.multiplechoice()
        checker = MultipleChoiceChecker(self.mc_data)
        walker = ParseTreeWalker()
        walker.walk(checker,tree)
        outcome = len(checker.error_list) == 0
        if outcome and not desired_outcome:
            extra_info = f"Je hebt geen enkel fout antwoord aangeduid."
        elif not outcome and desired_outcome:
            extra_info = "\n".join([f"Je hebt volgende fouten:"] + checker.error_list)
        else:
            extra_info = None
        return ((outcome,\
                 [(init_check_number,\
                   outcome,\
                   desired_outcome,\
                   # geen renderer als alles zoals verwacht is
                   None if outcome == desired_outcome else "text",\
                   extra_info)]),\
                init_check_number + 1)

class DisjunctiveCheck(CheckingPredicate):

    def __init__(self,disjuncts):
        self.disjuncts = disjuncts

    def mentioned_files(self,exercise_name):
        return set([fn for disjunct in self.disjuncts for fn in disjunct.mentioned_files(exercise_name)])

    def instructions(self,exercise_name,init_check_number):
        subinstructions = []
        next_init_check_number = init_check_number + 1
        for disjunct in self.disjuncts:
            (subinstruction_info,next_init_check_number) = disjunct.instructions(exercise_name,next_init_check_number)
            subinstructions.append(subinstruction_info)
        return (["Aan minstens een van volgende voorwaarden is voldaan:"] + subinstructions,next_init_check_number)

    def negative_instructions(self,exercise_name,init_check_number):
        subinstructions = []
        next_init_check_number = init_check_number + 1
        for disjunct in self.disjuncts:
            # note use of `negative_instructions`
            # De Morgan's law applied to disjunction
            (subinstruction_info,next_init_check_number) = disjunct.negative_instructions(exercise_name,next_init_check_number)
            subinstructions.append(subinstruction_info)
        return (['Aan al volgende voorwaarden is voldaan:'] + subinstructions,next_init_check_number)

    def component_checks(self):
        return [c for disjunct in self.disjuncts for c in disjunct.component_checks()]

    def check_submission(self,submission,student_path,model_path,desired_outcome,init_check_number,parent_is_negation=False):
        exit_code = False # assume
        next_check_number = init_check_number + 1
        analysis_children = []
        for disjunct in self.disjuncts:
            if not exit_code:
                ((child_result,child_analysis), next_check_number) = disjunct.check_submission(submission,student_path,model_path,desired_outcome,next_check_number)
                analysis_children += child_analysis
                exit_code = exit_code or child_result
            else:
                # still need to do this due to short circuiting and numbering, but don't run check
                # could add non-SC variant later on...
                (_,next_check_number) = disjunct.instructions(submission.content_uid,next_check_number)
        error_msg = None
        if exit_code != desired_outcome:
            if not parent_is_negation:
                error_msg = f"OR moest {desired_outcome} leveren, leverde {exit_code}"
            else:
                error_msg = f"AND moest {not desired_outcome} leveren, leverde {not exit_code}"
        return ((exit_code,\
                 [(init_check_number,exit_code,desired_outcome,"text" if exit_code != desired_outcome else None,error_msg)] + analysis_children),
                next_check_number)

class BatchType:
    """Elementair batchtype.

    Laat niets expliciet toe, maar checks die geen (eigen) side effect hebben, worden niet vermeld in component_checks.
    """

    description = "batchtype dat enkel checks zonder side effects aanvaardt"
    # moet enkel checks met potentiële side effects kennen
    allowed_checks = []

    @classmethod
    def can_cleanup(cls,exercises):
        # TODO: moet ook gebruikt worden
        return False

    @classmethod
    def cleanup(cls,student_dir,model_dir):
        pass

class Strategy:

    def __init__(self,refusing_check=Negation(TrueCheck()),accepting_check=Negation(TrueCheck())):
        self.refusing_check = refusing_check
        self.accepting_check = accepting_check

    def mentioned_files(self,exercise_name):
        return self.refusing_check.mentioned_files(exercise_name).union(self.accepting_check.mentioned_files(exercise_name))

    def component_checks(self):
        return self.refusing_check.component_checks() + self.accepting_check.component_checks()

    def instructions(self,exercise_name):
        (ref_instructions,ctr) = self.refusing_check.instructions(exercise_name,1)
        (acc_instructions,_) = self.accepting_check.instructions(exercise_name,ctr)
        return (ref_instructions,acc_instructions)
 
    def check_submission(self,submission,student_path,model_path):
        # new format analysis is
        # 1) number of instruction in instruction parse tree under depth-first traversal, ignoring negations, using None for other errors
        # 2) actual outcome
        # 3) expected outcome
        # 4) format name for extra explanation (or None if explanation is None)
        # 5) explanation in said format (or None)
        (outcome_refusing,analysis_refusing) = (None,[])
        (outcome_accepting,analysis_accepting) = (None,[])
        try:
            ((outcome_refusing,analysis_refusing),init_accepting_check_number) = self.refusing_check.check_submission(submission,student_path,model_path,desired_outcome=False,init_check_number=1)
            if outcome_refusing:
                return (SubmissionState.NEW_REFUSED,analysis_refusing)
            ((outcome_accepting,analysis_accepting),_) = self.accepting_check.check_submission(submission,student_path,model_path,desired_outcome=True,init_check_number=init_accepting_check_number)
            if outcome_accepting:
                return (SubmissionState.ACCEPTED,analysis_accepting)
        except Exception as e:
            logger.exception('Fout bij controle submissie: %s',e)
        print(f'Submissie die niet beslist kon worden. Outcome refusing was {outcome_refusing} en outcome accepting was {outcome_accepting}')
        logger.warning(f'Submissie die niet beslist kon worden. Outcome refusing was {outcome_refusing} en outcome accepting was {outcome_accepting}')
        return (SubmissionState.PENDING,[(None,None,None,"text",f"Het systeem kan niet automatisch bepalen of je inzending klopt. De lector wordt verwittigd. Weigering was {outcome_refusing} en aanvaarding was {outcome_accepting}")] + analysis_refusing + analysis_accepting)

# order is important for selection dropdowns
batch_types = [BatchType] + list(BatchType.__subclasses__())
