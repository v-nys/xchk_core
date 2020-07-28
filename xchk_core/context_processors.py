from .courses import courses
def courses_context(request):
    return {'courses' : courses}
