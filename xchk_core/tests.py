import unittest
from django.test import TestCase
from unittest.mock import Mock, patch, MagicMock
from bs4 import BeautifulSoup
from xchk_core.models import Submission, Repo
from xchk_core.strats import *
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
        analysis = strat.check_submission(submission,'/tmp/student')
        print(analysis)
        self.assertTrue(False)

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

class RepoFormTest(TestCase):

    def test_can_import(self):
        import xchk_core.forms
        self.assertTrue(True)

if __name__ == '__main__':
    unittest.main()

