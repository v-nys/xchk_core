from . import contentviews as cv
import importlib
import os
from django.conf import settings
from iteration_utilities import first

class Course:

    def __init__(self,uid,desc,structure):
        self.uid = uid
        self.description = desc
        self.structure = structure

    def predecessors(self,cv):
        # could be optimized, but computation should be small enough
        def _predecessors(cvs):
            num = len(cvs)
            for cv in set(cvs): # copy to avoid iterating and mutating simultaneously
                direct_predecessors = first(self.structure,default=(cv,[]),pred=lambda x: x[0] == cv)[1]
                for dp in direct_predecessors:
                    cvs.add(dp)
            if len(cvs) == num:
                return cvs
            else:
                return _predecessors(cvs)
        rec = _predecessors({cv})
        rec.remove(cv)
        return rec

def courses():
    course_dict = {}
    for (k,v) in settings.XCHK_SOURCE_COURSES.items():
        course_module = importlib.import_module(f'{v}.course')
        course = course_module.course
        course_dict[course.uid] = course
    return course_dict

# TODO: maybe memoize in the future?
def invert_edges(dependency_graph):
    inverted = []
    for (dependent,dependencies) in dependency_graph:
        for dependency in dependencies:
            existing_pairs = list(filter(lambda x: x[0] is dependency, inverted))
            list_of_dependents = existing_pairs[0][1] if existing_pairs else []
            if not list_of_dependents:
                inverted.append((dependency,list_of_dependents))
            list_of_dependents.append(dependent)
    return inverted

def tocify(course,inverted_course):
    def _dependency_pair_to_lst(pair):
        def _default_entry(dependent):
            return first(inverted_course,default=(dependent,[]),pred=lambda x: x[0] == dependent)
        dependents = pair[1]
        rec = [_dependency_pair_to_lst(_default_entry(dependent)) for dependent in dependents]
        return [pair[0]] + rec
    independent_cvs = [x[0] for x in course if x[1] == []]
    return [_dependency_pair_to_lst(pair) for pair in inverted_course if pair[0] in independent_cvs]
