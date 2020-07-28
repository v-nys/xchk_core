# Generated from MultipleChoice.g4 by ANTLR 4.8
# encoding: utf-8
from antlr4 import *
from io import StringIO
import sys
if sys.version_info[1] > 5:
	from typing import TextIO
else:
	from typing.io import TextIO


def serializedATN():
    with StringIO() as buf:
        buf.write("\3\u608b\ua72a\u8133\ub9ed\u417c\u3be7\u7786\u5964\3\6")
        buf.write("\22\4\2\t\2\4\3\t\3\3\2\6\2\b\n\2\r\2\16\2\t\3\3\3\3\6")
        buf.write("\3\16\n\3\r\3\16\3\17\3\3\2\2\4\2\4\2\2\2\21\2\7\3\2\2")
        buf.write("\2\4\13\3\2\2\2\6\b\5\4\3\2\7\6\3\2\2\2\b\t\3\2\2\2\t")
        buf.write("\7\3\2\2\2\t\n\3\2\2\2\n\3\3\2\2\2\13\r\7\4\2\2\f\16\7")
        buf.write("\3\2\2\r\f\3\2\2\2\16\17\3\2\2\2\17\r\3\2\2\2\17\20\3")
        buf.write("\2\2\2\20\5\3\2\2\2\4\t\17")
        return buf.getvalue()


class MultipleChoiceParser ( Parser ):

    grammarFileName = "MultipleChoice.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [  ]

    symbolicNames = [ "<INVALID>", "LETTER", "INT", "WS", "LINE_COMMENT" ]

    RULE_multiplechoice = 0
    RULE_qa = 1

    ruleNames =  [ "multiplechoice", "qa" ]

    EOF = Token.EOF
    LETTER=1
    INT=2
    WS=3
    LINE_COMMENT=4

    def __init__(self, input:TokenStream, output:TextIO = sys.stdout):
        super().__init__(input, output)
        self.checkVersion("4.8")
        self._interp = ParserATNSimulator(self, self.atn, self.decisionsToDFA, self.sharedContextCache)
        self._predicates = None




    class MultiplechoiceContext(ParserRuleContext):

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def qa(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(MultipleChoiceParser.QaContext)
            else:
                return self.getTypedRuleContext(MultipleChoiceParser.QaContext,i)


        def getRuleIndex(self):
            return MultipleChoiceParser.RULE_multiplechoice

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterMultiplechoice" ):
                listener.enterMultiplechoice(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitMultiplechoice" ):
                listener.exitMultiplechoice(self)




    def multiplechoice(self):

        localctx = MultipleChoiceParser.MultiplechoiceContext(self, self._ctx, self.state)
        self.enterRule(localctx, 0, self.RULE_multiplechoice)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 5 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 4
                self.qa()
                self.state = 7 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not (_la==MultipleChoiceParser.INT):
                    break

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class QaContext(ParserRuleContext):

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def INT(self):
            return self.getToken(MultipleChoiceParser.INT, 0)

        def LETTER(self, i:int=None):
            if i is None:
                return self.getTokens(MultipleChoiceParser.LETTER)
            else:
                return self.getToken(MultipleChoiceParser.LETTER, i)

        def getRuleIndex(self):
            return MultipleChoiceParser.RULE_qa

        def enterRule(self, listener:ParseTreeListener):
            if hasattr( listener, "enterQa" ):
                listener.enterQa(self)

        def exitRule(self, listener:ParseTreeListener):
            if hasattr( listener, "exitQa" ):
                listener.exitQa(self)




    def qa(self):

        localctx = MultipleChoiceParser.QaContext(self, self._ctx, self.state)
        self.enterRule(localctx, 2, self.RULE_qa)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 9
            self.match(MultipleChoiceParser.INT)
            self.state = 11 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 10
                self.match(MultipleChoiceParser.LETTER)
                self.state = 13 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not (_la==MultipleChoiceParser.LETTER):
                    break

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx





