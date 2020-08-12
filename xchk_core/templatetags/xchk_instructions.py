from django import template
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
import functools
from xchk_core.strats import StratInstructions

register = template.Library()

def iterable(obj):
    try:
        iter(obj)
    except Exception:
        return False
    else:
        return True

def _node_instructions_2_ul(instructions):
    instructions = StratInstructions(*instructions)
    def _folded(acc,elem):
        (acc_txt,before_ctr) = acc
        (elem_txt,after_ctr) = _aux(elem,before_ctr)
        return (acc_txt + elem_txt,after_ctr)
    def _aux(lst_or_str,li_counter):
        if isinstance(lst_or_str,str):
            return (f'<li><span id="instruction-{li_counter}">{lst_or_str}</span></li>',li_counter+1)
        elif len(lst_or_str) == 1:
            return _aux(lst_or_str[0],li_counter)
        else:
            (rec_txt,rec_ctr) = functools.reduce(_folded,lst_or_str[1:],("",li_counter+1))
            return (f'<li><span id="instruction-{li_counter}">{lst_or_str[0]}</span><ul>{rec_txt}</ul></li>',rec_ctr)
    (ref_elems,ctr) = _aux(instructions.refusing,1)
    (acc_elems,ctr) = _aux(instructions.accepting,ctr)
    return f'''<ul>
                 <li>Je oefening wordt geweigerd als:<ul>{ref_elems}</ul></li>
                 <li>Je oefening wordt aanvaard als:<ul>{acc_elems}</ul></li>
               </ul>'''

def _nested_conditional_escape(lst):
    return [conditional_escape(e) if isinstance(e,str)\
                                  else _nested_conditional_escape(e) if iterable(e)\
                                  else e\
            for e in lst]

@register.filter(needs_autoescape=True)
def node_instructions_2_ul(value, autoescape=True):
    if autoescape:
        escaped_value = _nested_conditional_escape(value)
    else:
        escaped_value = value
    return mark_safe(_node_instructions_2_ul(escaped_value))
