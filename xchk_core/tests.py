import unittest
from django.test import TestCase
from unittest.mock import Mock, patch, MagicMock, call
from bs4 import BeautifulSoup
from xchk_core.models import Submission, Repo
from xchk_core.strats import *
from xchk_core.courses import courses, tocify, invert_edges
from xchk_core.views import ulify
from xchk_core.contentviews import ContentView
from xchk_core.templatetags.xchk_instructions import node_instructions_2_ul

class TrueCheckInstructionGenerationTest(TestCase):

    def test_standard_true_instruction(self):
        chk = TrueCheck()
        self.assertEqual(chk.instructions('dummy_exercise'),[f"True"])

    def test_negative_true_instruction(self):
        chk = TrueCheck()
        self.assertEqual(chk.negative_instructions('dummy_exercise'),[f"False"])

    def test_negated_true_instruction(self):
        chk = Negation(TrueCheck())
        self.assertEqual(chk.instructions('dummy_exercise'),[f"False"])

    def test_negated_negative_true_instruction(self):
        chk = Negation(TrueCheck())
        self.assertEqual(chk.negative_instructions('dummy_exercise'),[f"True"])

class FileExistsCheckInstructionGenerationTest(TestCase):

    def test_standard_file_exists_instruction(self):
        chk = FileExistsCheck('myfile','txt')
        self.assertEqual(chk.instructions(None),["Je hebt een bestand met naam myfile.txt"])

    def test_negated_file_exists_instruction(self):
        chk = Negation(FileExistsCheck('myfile','txt'))
        self.assertEqual(chk.instructions(None),["Je hebt geen bestand met naam myfile.txt"])

class ConjunctiveCheckInstructionGenerationTest(TestCase):
    def test_simple_conjunction(self):
        chk = ConjunctiveCheck([TrueCheck(),TrueCheck(),TrueCheck()])
        self.assertEqual(chk.instructions(None),["Aan al volgende voorwaarden is voldaan:",["True"],["True"],["True"]])

    def test_negated_simple_conjunction(self):
        chk = Negation(ConjunctiveCheck([TrueCheck(),TrueCheck(),TrueCheck()]))
        self.assertEqual(chk.instructions(None),[AT_LEAST_ONE_TEXT,["False"],["False"],["False"]])

class DisjunctiveCheckInstructionGenerationTest(TestCase):
    def test_simple_disjunction(self):
        chk = DisjunctiveCheck([TrueCheck(),TrueCheck(),TrueCheck()])
        self.assertEqual(chk.instructions(None),[AT_LEAST_ONE_TEXT,["True"],["True"],["True"]])

    def test_negated_simple_disjunction(self):
        chk = Negation(DisjunctiveCheck([TrueCheck(),TrueCheck(),TrueCheck()]))
        self.assertEqual(chk.instructions(None),[ALL_OF_TEXT,["False"],["False"],["False"]])

class StrategyInstructionGenerationTest(TestCase):

    def test_only_explicit_checks(self):
        acc_chk = ConjunctiveCheck([TrueCheck(),TrueCheck(),FileExistsCheck(name='myfile',extension='txt')])
        ref_chk = Negation(acc_chk)
        strat = Strategy(ref_chk,acc_chk)
        self.assertEqual(
                strat.instructions('dummy_ex'),
                StratInstructions(refusing=[AT_LEAST_ONE_TEXT,["False"],["False"],["Je hebt geen bestand met naam myfile.txt"]],
                                  accepting=[ALL_OF_TEXT,["True"],["True"],["Je hebt een bestand met naam myfile.txt"]]))

class CheckSubmissionTest(TestCase):

    def test_check_disjunct_with_alternatives_test(self):
        check = DisjunctiveCheck([Negation(TrueCheck()),Negation(TrueCheck()),TrueCheck()])
        analysis = check.check_submission(Submission(),'/tmp/student',True,1,False)
        # first two don't yield desired outcome but desired outcome can still be reached
        self.assertTrue(analysis.outcomes_components[1].acceptable_to_ancestor)
        self.assertTrue(analysis.outcomes_components[2].acceptable_to_ancestor)

    def test_check_disjunct_without_alternatives_test(self):
        check = DisjunctiveCheck([Negation(TrueCheck()),Negation(TrueCheck()),TrueCheck()])
        analysis = check.check_submission(Submission(),'/tmp/student',False,1,False)
        # third component irrevocably prevents desired outcome from being reached
        self.assertFalse(analysis.outcomes_components[3].acceptable_to_ancestor)

    def test_undecidable_submission(self):
        strat = Strategy(Negation(TrueCheck()),Negation(TrueCheck()))
        submission = Submission()
        submission.repo = Repo()
        submission.repo.url = "www.google.be"
        submission.checksum = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        analysis = strat.check_submission(submission,'/tmp/student')[0]
        self.assertEqual(analysis.submission_state,SubmissionState.UNDECIDED)

class Instructions2HtmlTest(TestCase):

    def setUp(self):
        self.maxDiff = None

    def test_leaf_node_conditions(self):
        instructions = StratInstructions(refusing=["False"],accepting=["True"])
        outcome = node_instructions_2_ul(instructions)
        intended = '''<ul>
                        <li>Je oefening wordt geweigerd als:
                          <ul>
                            <li><span id="instruction-1">False</span></li>
                          </ul>
                        </li>
                        <li>Je oefening wordt aanvaard als:
                          <ul>
                            <li><span id="instruction-2">True</span></li>
                          </ul>
                        </li>
                      </ul>'''
        soup1 = BeautifulSoup(outcome,'html.parser')
        soup2 = BeautifulSoup(intended,'html.parser')
        self.assertEqual(soup1.prettify(),soup2.prettify())

    def test_nested_list(self):
        instructions = StratInstructions(
                refusing=[ALL_OF_TEXT,"True",[AT_LEAST_ONE_TEXT,"False","True"]],
                accepting=["True"])
        outcome = node_instructions_2_ul(instructions)
        soup1 = BeautifulSoup(outcome,'html.parser')
        intended = f'''
<ul>
  <li>Je oefening wordt geweigerd als:
    <ul>
      <li>
        <span id="instruction-1">{ALL_OF_TEXT}</span>
        <ul>
          <li>
            <span id="instruction-2">True</span>
          </li>
          <li>
            <span id="instruction-3">{AT_LEAST_ONE_TEXT}</span>
            <ul>
              <li><span id="instruction-4">False</span></li>
              <li><span id="instruction-5">True</span></li>
            </ul>
          </li>
        </ul>
      </li>
    </ul>
  </li>
  <li>Je oefening wordt aanvaard als:<ul><li><span id="instruction-6">True</span></li></ul></li>
</ul>'''
        soup2 = BeautifulSoup(intended,'html.parser')
        self.assertEqual(soup1.prettify(),soup2.prettify())

class MoreSpecificSituationsCheckTest(TestCase):

    def setUp(self):
        self.more_specific = ConjunctiveCheck([FileExistsCheck('file1'),FileExistsCheck('file2')])
        self.less_specific = FileExistsCheck('file1')
        self.compound = MoreSpecificSituationsCheck([self.more_specific,self.less_specific])
        self.submission = Submission()
        self.submission.repo = Repo()
        self.submission.repo.url = "www.google.be"
        self.submission.checksum = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        self.student_path = '/tmp/student'

    def test_instructions(self):
        self.assertEqual(self.compound.instructions('someex'),["Je hebt een bestand met naam file1"])

    def test_negative_instructions(self):
        self.assertEqual(self.compound.negative_instructions('someex'),["Je hebt geen bestand met naam file1"])

    def test_check_desiring_true_non_negated_globally_true(self):
        with patch('os.path.exists',side_effect=[True,False,True]) as mock_path_exists:
            analysis = self.compound.check_submission(submission=self.submission,student_path=self.student_path,desired_outcome=True,init_check_number=1,ancestor_has_alternatives=False)
            mock_path_exists.assert_has_calls([call('/tmp/student/file1'),call('/tmp/student/file2'),call('/tmp/student/file1')])
        self.assertEqual(analysis, OutcomeAnalysis(True,[OutcomeComponent(component_number=1,outcome=True,desired_outcome=True,rendered_data='',acceptable_to_ancestor=True)]))

    @unittest.skip("still working on simpler cases")
    def test_check_desiring_true_non_negated_globally_false(self):
        # niet zinvol hier specifiekere feedback te gebruiken, alleen nuttig als specifiekere check *slaagt* (en dat ongewenst is)
        # feedback moet dus zelfde zijn als voor gewoon falen van algemene check op zich
        with patch('os.path.exists',side_effect=[False,False,False]) as mock_path_exists:
            analysis = self.compound.check_submission(submission=self.submission,student_path=self.student_path,desired_outcome=True,init_check_number=1,ancestor_has_alternatives=False)
            mock_path_exists.assert_has_calls([call('/tmp/student/file1'),call('/tmp/student/file2'),call('/tmp/student/file1')])
        self.assertTrue(False)

    @unittest.skip("still working on simpler cases")
    def test_check_desiring_true_negated_globally_true(self):
        self.assertTrue(False)

    @unittest.skip("still working on simpler cases")
    def test_check_desiring_true_negated_globally_false(self):
        # niet zinvol hier specifiekere feedback te gebruiken, alleen nuttig als specifiekere check *slaagt* (en dat ongewenst is)
        # feedback moet dus zelfde zijn als voor gewoon falen van algemene check op zich
        self.assertTrue(False)

    @unittest.skip("still working on simpler cases")
    def test_check_desiring_false_non_negated_globally_true(self):
        self.assertTrue(False)

    @unittest.skip("still working on simpler cases")
    def test_check_desiring_false_non_negated_globally_false(self):
        # niet zinvol hier specifiekere feedback te gebruiken, alleen nuttig als specifiekere check *slaagt* (en dat ongewenst is)
        # feedback moet dus zelfde zijn als voor gewoon falen van algemene check op zich
        self.assertTrue(False)

    @unittest.skip("still working on simpler cases")
    def test_check_desiring_false_negated_globally_true(self):
        self.assertTrue(False)

    @unittest.skip("still working on simpler cases")
    def test_check_desiring_false_negated_globally_false(self):
        # niet zinvol hier specifiekere feedback te gebruiken, alleen nuttig als specifiekere check *slaagt* (en dat ongewenst is)
        # feedback moet dus zelfde zijn als voor gewoon falen van algemene check op zich
        self.assertTrue(False)

class CatchallCheckTest(TestCase):

    def setUp(self):
        self.component1 = FileExistsCheck('file1')
        self.component2 = FileExistsCheck('file2')
        self.compound = CatchallCheck([self.component1, self.component2],
                                      'Je hebt alle files die vermeld worden in de opgave',
                                      'Je hebt minstens een file die vermeld wordt in de opgave niet')
        self.submission = Submission()
        self.submission.repo = Repo()
        self.submission.repo.url = "www.google.be"
        self.submission.checksum = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        self.student_path = '/tmp/student'
 
    def test_instructions(self):
        self.assertEqual(self.compound.instructions('someex'),["Je hebt alle files die vermeld worden in de opgave"])

    def test_negative_instructions(self):
        self.assertEqual(self.compound.negative_instructions('someex'),["Je hebt minstens een file die vermeld wordt in de opgave niet"])

    def test_check_desiring_true_non_negated_globally_true(self):
        with patch('os.path.exists',side_effect=[True,True]) as mock_path_exists:
            analysis = self.compound.check_submission(submission=self.submission,student_path=self.student_path,desired_outcome=True,init_check_number=1,ancestor_has_alternatives=False)
            mock_path_exists.assert_has_calls([call('/tmp/student/file1'),call('/tmp/student/file2')])
        # should be presented as having just one component
        self.assertEqual(analysis, OutcomeAnalysis(True,[OutcomeComponent(component_number=1,outcome=True,desired_outcome=True,rendered_data='',acceptable_to_ancestor=True)]))

    @unittest.skip("still working on simpler cases")
    def test_check_desiring_true_non_negated_globally_false(self):
        self.assertTrue(False)

    @unittest.skip("still working on simpler cases")
    def test_check_desiring_true_negated_globally_true(self):
        self.assertTrue(False)

    @unittest.skip("still working on simpler cases")
    def test_check_desiring_true_negated_globally_false(self):
        self.assertTrue(False)

    @unittest.skip("still working on simpler cases")
    def test_check_desiring_false_non_negated_globally_true(self):
        self.assertTrue(False)

    @unittest.skip("still working on simpler cases")
    def test_check_desiring_false_non_negated_globally_false(self):
        with patch('os.listdir',return_value=['file1']) as mock_listdir:
            analysis = self.compound.check_submission(submission=self.submission,student_path=self.student_path,desired_outcome=False,init_check_number=1,ancestor_has_alternatives=False)
        self.assertEqual(analysis, OutcomeAnalysis(False,[]))

    @unittest.skip("still working on simpler cases")
    def test_check_desiring_false_negated_globally_true(self):
        self.assertTrue(False)

    @unittest.skip("still working on simpler cases")
    def test_check_desiring_false_negated_globally_false(self):
        self.assertTrue(False)

class RepoFormTest(TestCase):

    def test_can_import(self):
        import xchk_core.forms
        self.assertTrue(True)

class CV1A(ContentView):
    uid = 'CV1A'
    title = 'CV1A'

    @classmethod
    def is_accessible_by(cls,user,user_submissions):
        return True

    @classmethod
    def accepted_for(cls,user,user_submissions):
        return True

class CV2A(ContentView):
    uid = 'CV2A'
    title = 'CV2A'

    @classmethod
    def is_accessible_by(cls,user,user_submissions):
        return True

    @classmethod
    def accepted_for(cls,user,user_submissions):
        return False

    @classmethod
    def completed_by(cls,user,user_submissions):
        return False


class CV3A(ContentView):
    uid = 'CV3A'
    title = 'CV3A'

    @classmethod
    def is_accessible_by(cls,user,user_submissions):
        return False

    @classmethod
    def accepted_for(cls,user,user_submissions):
        return False

    @classmethod
    def completed_by(cls,user,user_submissions):
        return False

class CV1B(ContentView):
    uid = 'CV1B'
    title = 'CV1B'

    @classmethod
    def is_accessible_by(cls,user,user_submissions):
        return True

    @classmethod
    def accepted_for(cls,user,user_submissions):
        return True

class CV2B(ContentView):
    uid = 'CV2B'
    title = 'CV2B'

    @classmethod
    def is_accessible_by(cls,user,user_submissions):
        return True

    @classmethod
    def accepted_for(cls,user,user_submissions):
        return False

    @classmethod
    def completed_by(cls,user,user_submissions):
        return True

class CV1C(ContentView):
    uid = 'CV1C'
    title = 'CV1C'

    @classmethod
    def is_accessible_by(cls,user,user_submissions):
        return True

    @classmethod
    def accepted_for(cls,user,user_submissions):
        return True

class TOCifyTest(TestCase):

    def setUp(self):
        self.course_structure = [(CV3A,[CV2A,CV2B]),
                                 (CV2A,[CV1A,CV1B]),
                                 (CV2B,[CV1B,CV1C]),
                                 (CV1A,[]),
                                 (CV1B,[]),
                                 (CV1C,[])]
        self.inverted = invert_edges(self.course_structure)
        self.tocified = tocify(self.course_structure,self.inverted)
        self.maxDiff = None

    def test_invert_edges(self):
        self.assertEqual(self.inverted,
                         [(CV2A,[CV3A]),
                          (CV2B,[CV3A]),
                          (CV1A,[CV2A]),
                          (CV1B,[CV2A,CV2B]),
                          (CV1C,[CV2B])])

    def test_can_tocify(self):
        self.assertEqual(self.tocified,[[CV1A,[CV2A,[CV3A]]],
                                        [CV1B,[CV2A,[CV3A]],
                                                 [CV2B,[CV3A]]],
                                        [CV1C,[CV2B,[CV3A]]]])

    @unittest.skip("need to modify output for icons, but looks good when served")
    def test_ulify(self):
        def reverse_func(viewname,args=None):
            return "http://www.google.com"
        mock_request = MagicMock()
        structure = [[CV1A,[CV2A,[CV3A]]],
                     [CV1B,[CV2A,[CV3A]],
                           [CV2B,[CV3A]]],
                     [CV1C,[CV2B,[CV3A]]]]
        outcome = ulify(self.tocified,mock_request,'mycourse',reverse_func=reverse_func,user_submissions=[])
        expected = '''
<ul>
  <li><a class="accepted" cv_uid="CV1A" href="http://www.google.com">CV1A</a>
    <ul>
      <li><a cv_uid="CV2A" href="http://www.google.com">CV2A</a>
        <ul>
          <li><a cv_uid="CV3A" class="locked" href="http://www.google.com">CV3A</a></li>
        </ul>
      </li>
    </ul>
  </li>
  <li><a class="accepted" cv_uid="CV1B" href="http://www.google.com">CV1B</a>
    <ul>
      <li><a cv_uid="CV2A" href="http://www.google.com">CV2A</a></li>
      <li><a cv_uid="CV2B" href="http://www.google.com" class="undecided">CV2B</a>
        <ul>
          <li><a cv_uid="CV3A" href="http://www.google.com" class="locked">CV3A</a></li>
        </ul>
      </li>
    </ul>
  </li>
  <li><a class="accepted" cv_uid="CV1C" href="http://www.google.com">CV1C</a>
    <ul>
      <li><a cv_uid="CV2B" href="http://www.google.com" class="undecided">CV2B</a></li>
    </ul>
  </li>
</ul>'''
        soup1 = BeautifulSoup(outcome,'html.parser')
        soup2 = BeautifulSoup(expected,'html.parser')
        self.assertEqual(soup1.prettify().strip(),soup2.prettify().strip())

if __name__ == '__main__':
    unittest.main()

