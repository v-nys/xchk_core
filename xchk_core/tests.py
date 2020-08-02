import unittest
from django.test import TestCase
from unittest.mock import Mock, patch, MagicMock
from bs4 import BeautifulSoup
from xchk_core.models import SubmissionV2
from xchk_core.strats import *
from xchk_core.templatetags.xchk_instructions import node_instructions_2_ul

class TrueCheckInstructionGenerationTest(TestCase):

    def test_standard_true_instruction(self):
        chk = TrueCheck()
        self.assertEqual(chk.instructions('dummy_exercise'),[f"True"])

    def test_negative_true_instruction(self):
        chk = TrueCheck()
        self.assertEqual(chk.negative_instructions('dummy_exercise'),[f"False"])

    def test_implicit_true_instruction(self):
        chk = TrueCheck(implicit=True)
        self.assertEqual(chk.instructions('dummy_exercise'),[])

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

    def test_implicit_file_exists_instruction(self):
        chk = FileExistsCheck('myfile','txt',implicit=True)
        self.assertEqual(chk.instructions('dummy_exercise'),[])

class ConjunctiveCheckInstructionGenerationTest(TestCase):
    def test_simple_conjunction(self):
        chk = ConjunctiveCheck([TrueCheck(),TrueCheck(),TrueCheck()])
        self.assertEqual(chk.instructions(None),["Aan al volgende voorwaarden is voldaan:",["True"],["True"],["True"]])

    def test_negated_simple_conjunction(self):
        chk = Negation(ConjunctiveCheck([TrueCheck(),TrueCheck(),TrueCheck()]))
        self.assertEqual(chk.instructions(None),[AT_LEAST_ONE_TEXT,["False"],["False"],["False"]])

    def test_conjunction_with_several_explicit_elements(self):
        chk = ConjunctiveCheck([TrueCheck(),TrueCheck(implicit=True),TrueCheck()])
        self.assertEqual(chk.instructions(None),["Aan al volgende voorwaarden is voldaan:",["True"],["True"]])

    @unittest.skip("optimization, can wait")
    def test_conjunction_with_one_explicit_element(self):
        chk = ConjunctiveCheck([TrueCheck(),TrueCheck(implicit=True),TrueCheck(implicit=True)])
        self.assertEqual(chk.instructions(None),["True"])

    @unittest.skip("optimization, can wait")
    def test_negated_conjunction_with_one_explicit_element(self):
        chk = Negation(ConjunctiveCheck([TrueCheck(),TrueCheck(implicit=True),TrueCheck(implicit=True)]))
        self.assertEqual(chk.instructions(None),["False"])

    @unittest.skip("optimization, can wait")
    def test_conjunction_without_elements(self):
        chk = ConjunctiveCheck([TrueCheck(implicit=True),TrueCheck(implicit=True),TrueCheck(implicit=True)])
        self.assertEqual(chk.instructions(None),[])

    @unittest.skip("optimization, can wait")
    def test_negated_conjunction_without_elements(self):
        chk = Negation(ConjunctiveCheck([TrueCheck(implicit=True),TrueCheck(implicit=True),TrueCheck(implicit=True)]))
        self.assertEqual(chk.instructions(None),[])


class DisjunctiveCheckInstructionGenerationTest(TestCase):
    def test_simple_disjunction(self):
        chk = DisjunctiveCheck([TrueCheck(),TrueCheck(),TrueCheck()])
        self.assertEqual(chk.instructions(None),[AT_LEAST_ONE_TEXT,["True"],["True"],["True"]])

    def test_negated_simple_disjunction(self):
        chk = Negation(DisjunctiveCheck([TrueCheck(),TrueCheck(),TrueCheck()]))
        self.assertEqual(chk.instructions(None),[ALL_OF_TEXT,["False"],["False"],["False"]])

    @unittest.skip("optimization, can wait")
    def test_optimizations(self):
        # TODO: same optimizations as for conjunctions
        self.assertTrue(False)

class StrategyInstructionGenerationTest(TestCase):

    def test_only_explicit_checks(self):
        acc_chk = ConjunctiveCheck([TrueCheck(),TrueCheck(),FileExistsCheck(name='myfile',extension='txt')])
        ref_chk = Negation(acc_chk)
        strat = Strategy(ref_chk,acc_chk)
        self.assertEqual(
                strat.instructions('dummy_ex'),
                StratInstructions(refusing=[AT_LEAST_ONE_TEXT,["False"],["False"],["Je hebt geen bestand met naam myfile.txt"]],
                                  implicit_refusing_components=False,
                                  accepting=[ALL_OF_TEXT,["True"],["True"],["Je hebt een bestand met naam myfile.txt"]],
                                  implicit_accepting_components=False))

    def test_implicit_refusing_explicit_accepting_checks(self):
        acc_chk = ConjunctiveCheck([TrueCheck(),TrueCheck(),FileExistsCheck(name='myfile',extension='txt')])
        ref_chk = Negation(ConjunctiveCheck([TrueCheck(),TrueCheck(implicit=True),FileExistsCheck(name='myfile',extension='txt')]))
        strat = Strategy(ref_chk,acc_chk)
        self.assertEqual(
                strat.instructions('dummy_ex'),
                StratInstructions(refusing=[AT_LEAST_ONE_TEXT,["False"],["Je hebt geen bestand met naam myfile.txt"]],
                                  implicit_refusing_components=True,
                                  accepting=[ALL_OF_TEXT,["True"],["True"],["Je hebt een bestand met naam myfile.txt"]],
                                  implicit_accepting_components=False))

    def test_explicit_refusing_implicit_accepting_checks(self):
        acc_chk = ConjunctiveCheck([TrueCheck(),TrueCheck(implicit=True),FileExistsCheck(name='myfile',extension='txt')])
        ref_chk = Negation(ConjunctiveCheck([TrueCheck(),TrueCheck(),FileExistsCheck(name='myfile',extension='txt')]))
        strat = Strategy(ref_chk,acc_chk)
        self.assertEqual(
                strat.instructions('dummy_ex'),
                StratInstructions(refusing=[AT_LEAST_ONE_TEXT,["False"],["False"],["Je hebt geen bestand met naam myfile.txt"]],
                                  implicit_refusing_components=False,
                                  accepting=[ALL_OF_TEXT,["True"],["Je hebt een bestand met naam myfile.txt"]],
                                  implicit_accepting_components=True))

class Instructions2HtmlTest(TestCase):

    @unittest.skip("dealing with exact representation of whitespace is painful, use parsed representation")
    def test_no_element_list(self):
        # FIXME: think I need a StrategyInstructions object and not a single list here
        self.assertTrue(False)
        self.assertEqual(node_instructions_2_ul([],"<ul></ul>"))

    @unittest.skip("dealing with exact representation of whitespace is painful, use parsed representation")
    def test_single_element_list(self):
        # FIXME: think I need a StrategyInstructions object and not a single list here
        self.assertTrue(False)
        self.assertEqual(node_instructions_2_ul(["True"],'<ul><li><a href="#explanation-1">True</a></li></ul>'))

    @unittest.skip("dealing with exact representation of whitespace is painful, use parsed representation")
    def test_flat_list(self):
        # FIXME: think I need a StrategyInstructions object and not a single list here
        self.assertTrue(False)
        self.assertEqual(node_instructions_2_ul(["True","False"],'<ul><li><a href="#explanation-1">True</a></li><li><a href="#explanation-2">False</a></li></ul>'))

    def test_nested_list(self):
        instructions = StratInstructions(
                refusing=[ALL_OF_TEXT,"True",[AT_LEAST_ONE_TEXT,"False","True"]],
                implicit_refusing_components=False,
                accepting=["True"],
                implicit_accepting_components=False)
        outcome = node_instructions_2_ul(instructions)
        soup1 = BeautifulSoup(outcome,'html.parser')
        intended = f'''
<ul>
  <li>Je oefening wordt geweigerd als:
    <ul>
      <li>
        <a href="#explanation-1">{ALL_OF_TEXT}</a>
        <ul>
          <li>
            <a href="#explanation-2">True</a>
          </li>
          <li>
            <a href="#explanation-3">{AT_LEAST_ONE_TEXT}</a>
            <ul>
              <li><a href="#explanation-4">False</a></li>
              <li><a href="#explanation-5">True</a></li>
            </ul>
          </li>
        </ul>
      </li>
    </ul>
  </li>
  <li>Je oefening wordt aanvaard als:<ul><li><a href="#explanation-6">True</a></li></ul></li>
</ul>'''
        soup2 = BeautifulSoup(intended,'html.parser')
        self.assertEqual(soup1.prettify(),soup2.prettify())

if __name__ == '__main__':
    unittest.main()

