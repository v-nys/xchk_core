from django import template
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
import functools

register = template.Library()

def iterable(obj):
    try:
        iter(obj)
    except Exception:
        return False
    else:
        return True

def _node_instructions_2_ul(lst_or_str):
    def _folded(acc,elem):
        (acc_txt,before_ctr) = acc
        (elem_txt,after_ctr) = _aux(elem,before_ctr)
        return (acc_txt + elem_txt,after_ctr)
    def _aux(lst_or_str,li_counter):
        if isinstance(lst_or_str,str):
            return (f'<li><a href="#explanation-{li_counter}">{lst_or_str}</a></li>',li_counter+1)
        elif len(lst_or_str) == 1:
            return _aux(lst_or_str[0],li_counter)
        else:
            (rec_txt,rec_ctr) = functools.reduce(_folded,lst_or_str[1:],("",li_counter+1))
            return (f'<li><a href="#explanation-{li_counter}">{lst_or_str[0]}</a><ul>{rec_txt}</ul></li>',rec_ctr)
    (ref_elems,ctr) = _aux(lst_or_str[0],1)
    (acc_elems,ctr) = _aux(lst_or_str[1],ctr)
    return f'''<ul>
                 <li>Je oefening wordt geweigerd als:<ul>{ref_elems}</ul></li>
                 <li>Je oefening wordt aanvaard als:<ul>{acc_elems}</ul></li>
               </ul>'''
    #acc_ul = f'<ul>{_aux(lst_or_str,1)[1]}</ul>'
    #return f'<ul>{_aux(lst_or_str,1)[0]}</ul>'

def _mc_2_ul(lst):
    def _render_mc_item(item):
        return f'<li>{item[0]}<ol>{"".join(["<li>" + answer[0] + "</li>" for answer in item[1:]])}</ol></li>'
    return f'<ol class="multiple-choice">{"".join([_render_mc_item(el) for el in lst])}</ol>'

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

@register.filter(needs_autoescape=True)
def mc_2_ul(value, autoescape=True):
    if autoescape:
        escaped_value = _nested_conditional_escape(value)
    else:
        escaped_value = value
    return mark_safe(_mc_2_ul(escaped_value))
    # return mark_safe(str(value) + '<ul><li>WIP: moet mc_2_ul filter nog afwerken</li></ul>')
