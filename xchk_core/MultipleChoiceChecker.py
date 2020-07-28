from .MultipleChoiceListener import MultipleChoiceListener

class MultipleChoiceChecker(MultipleChoiceListener):

    letter_range = range(ord('a'),ord('z'))

    def __init__(self,mc_data):
        super().__init__()
        self.expected_idx = 1
        self.error_list = []
        self.mc_data = mc_data

    def enterQa(self,ctx):
        q_number = int(ctx.INT().getText())
        if q_number != self.expected_idx:
            self.error_list.append(f'Vraag {self.expected_idx} werd verwacht op de plaats waar {q_number} voorkomt.')
        self.expected_idx = q_number + 1
        if q_number > 0 and q_number <= len(self.mc_data):
            model_data = self.mc_data[q_number-1]
            # +1: answer indexes start at 1!
            # 0 is the question
            answers_as_indexes = [ord(l.getText().lower()) - ord('a') + 1 for l in ctx.LETTER()]
            model_indexes = [idx for (idx,(_answer_text,truth,_hint)) in enumerate(model_data[1:],start=1) if truth]
            # missing answer
            for a in model_indexes:
                # `and` because not every answer has an associated hint
                if a not in answers_as_indexes and model_data[a][2]:
                    self.error_list.append(f'Vraag {q_number}: {model_data[a][2]}')
            # incorrect answer
            for a in answers_as_indexes:
                if a not in model_indexes and model_data[a][2]:
                    self.error_list.append(f'Vraag {q_number}: {model_data[a][2]}')
        else:
            self.error_list.append(f'Vraag {q_number} is geen geldige index. Er zijn {len(self.mc_data)} vragen en deze worden geteld vanaf 1.')
