from . import contentviews as cv
import importlib
import os
import igraph
from django.conf import settings

class Course:

    def __init__(self,uid,desc,structure,solutions_url):
        self.uid = uid
        self.description = desc
        self.structure = structure
        self.solutions_url = solutions_url

def courses():
    course_dict = {}
    for (k,v) in settings.XCHK_SOURCE_COURSES.items():
        course_module = importlib.import_module(f'{v}.course')
        course = course_module.course
        course_dict[course.uid] = course
    return course_dict

# TODO: memoize?
def course_graphs():
    graphs = {}
    for course in courses():
        graph = igraph.Graph(directed=True)
        graphs[course] = graph
        node_set = set()
        for (dependent,dependencies) in courses()[course].structure:
            node_set.add(dependent)
            for dependency in dependencies:
                node_set.add(dependency)
        node_lst = list(node_set) # zo heeft alles meteen een nummer
        graph.add_vertices(len(node_lst))
        for (idx,content) in enumerate(node_lst):
            graph.vs[idx]["contentview"] = content
            graph.vs[idx]["label"] = content.uid
            graph.vs[idx]["id"] = content.uid
            graph.vs[idx]["title"] = content.uid
        # edges toevoegen... lastig, want info is er niet meer
        # zal gewoon nog eens moeten traversen
        for (dependent,dependencies) in courses()[course].structure:
            dependent_idx = [v.index for v in graph.vs if v["contentview"] == dependent][0]
            for dependency in dependencies:
                dependency_idx = [v.index for v in graph.vs if v["contentview"] == dependency][0]
                graph.add_edges([(dependency_idx,dependent_idx)])
    return graphs
