# Generated from MultipleChoice.g4 by ANTLR 4.8
from antlr4 import *
from io import StringIO
from typing.io import TextIO
import sys



def serializedATN():
    with StringIO() as buf:
        buf.write("\3\u608b\ua72a\u8133\ub9ed\u417c\u3be7\u7786\u5964\2\6")
        buf.write(")\b\1\4\2\t\2\4\3\t\3\4\4\t\4\4\5\t\5\3\2\3\2\3\3\6\3")
        buf.write("\17\n\3\r\3\16\3\20\3\4\6\4\24\n\4\r\4\16\4\25\3\4\3\4")
        buf.write("\3\5\3\5\3\5\3\5\7\5\36\n\5\f\5\16\5!\13\5\3\5\5\5$\n")
        buf.write("\5\3\5\3\5\3\5\3\5\3\37\2\6\3\3\5\4\7\5\t\6\3\2\5\4\2")
        buf.write("C\\c|\3\2\62;\5\2\13\f\17\17\"\"\2,\2\3\3\2\2\2\2\5\3")
        buf.write("\2\2\2\2\7\3\2\2\2\2\t\3\2\2\2\3\13\3\2\2\2\5\16\3\2\2")
        buf.write("\2\7\23\3\2\2\2\t\31\3\2\2\2\13\f\t\2\2\2\f\4\3\2\2\2")
        buf.write("\r\17\t\3\2\2\16\r\3\2\2\2\17\20\3\2\2\2\20\16\3\2\2\2")
        buf.write("\20\21\3\2\2\2\21\6\3\2\2\2\22\24\t\4\2\2\23\22\3\2\2")
        buf.write("\2\24\25\3\2\2\2\25\23\3\2\2\2\25\26\3\2\2\2\26\27\3\2")
        buf.write("\2\2\27\30\b\4\2\2\30\b\3\2\2\2\31\32\7\61\2\2\32\33\7")
        buf.write("\61\2\2\33\37\3\2\2\2\34\36\13\2\2\2\35\34\3\2\2\2\36")
        buf.write("!\3\2\2\2\37 \3\2\2\2\37\35\3\2\2\2 #\3\2\2\2!\37\3\2")
        buf.write("\2\2\"$\7\17\2\2#\"\3\2\2\2#$\3\2\2\2$%\3\2\2\2%&\7\f")
        buf.write("\2\2&\'\3\2\2\2\'(\b\5\2\2(\n\3\2\2\2\7\2\20\25\37#\3")
        buf.write("\b\2\2")
        return buf.getvalue()


class MultipleChoiceLexer(Lexer):

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    LETTER = 1
    INT = 2
    WS = 3
    LINE_COMMENT = 4

    channelNames = [ u"DEFAULT_TOKEN_CHANNEL", u"HIDDEN" ]

    modeNames = [ "DEFAULT_MODE" ]

    literalNames = [ "<INVALID>",
 ]

    symbolicNames = [ "<INVALID>",
            "LETTER", "INT", "WS", "LINE_COMMENT" ]

    ruleNames = [ "LETTER", "INT", "WS", "LINE_COMMENT" ]

    grammarFileName = "MultipleChoice.g4"

    def __init__(self, input=None, output:TextIO = sys.stdout):
        super().__init__(input, output)
        self.checkVersion("4.8")
        self._interp = LexerATNSimulator(self, self.atn, self.decisionsToDFA, PredictionContextCache())
        self._actions = None
        self._predicates = None


