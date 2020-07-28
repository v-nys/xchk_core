from MultipleChoiceListener import MultipleChoiceListener

class MultipleChoicePrinter(MultipleChoiceListener):

    def enterQa(self,ctx):
        print(ctx.INT())
        for l in ctx.LETTER():
            print(l.getText())
