from . import contentviews as cv
import importlib
import os
from django.conf import settings

class Course:

    def __init__(self,uid,desc,structure):
        self.uid = uid
        self.description = desc
        self.structure = structure

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
            existing_pair = list(filter(lambda x: x[0] is dependency, inverted))[0]
            list_of_dependents = existing_pair[1] if existing_pair else []
            if not list_of_dependents:
                inverted.append((dependency,list_of_dependents))
            list_of_dependents.append(dependent)
    return inverted
