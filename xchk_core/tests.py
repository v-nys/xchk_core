import unittest
from django.test import TestCase
from unittest.mock import Mock, patch, MagicMock
from xchk_core.models import SubmissionV2
from xchk_core.strats import *

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

    def test_conjunction_with_several_explicit_elements(self):
        chk = ConjunctiveCheck([TrueCheck(),TrueCheck(implicit=True),TrueCheck()])
        self.assertEqual(chk.instructions(None),["Aan al volgende voorwaarden is voldaan:",["True"],["True"]])

    @unittest.skip("optimization, can wait")
    def test_conjunction_with_one_explicit_element(self):
        chk = ConjunctiveCheck([TrueCheck(),TrueCheck(implicit=True),TrueCheck(implicit=True)])
        self.assertEqual(chk.instructions(None),["True"])

    @unittest.skip("optimization, can wait")
    def test_conjunction_without_elements(self):
        chk = ConjunctiveCheck([TrueCheck(implicit=True),TrueCheck(implicit=True),TrueCheck(implicit=True)])
        self.assertEqual(chk.instructions(None),[])

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

if __name__ == '__main__':
    unittest.main()

