from .courses import courses
# FIXME: staat hier geloof ik enkel om navbar in te vullen
# bovendien is courses daar een functie, dus vreemd om die terug te geven
def courses_context(request):
    return {'courses' : courses}
