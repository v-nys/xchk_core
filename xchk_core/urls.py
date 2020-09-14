from django.urls import path
from django.conf.urls import include

from . import views, contentviews

app_name = 'checkerapp'
urlpatterns = [
    path('', views.index_view, name='index'),
    path('create_repo', views.CreateRepoView.as_view(), name='create_repo'),
    path('content/impossible_node', contentviews.ImpossibleNodeView.as_view(), name=f'{contentviews.ImpossibleNodeView.uid}_view'),
    path('nodes/feedback/<int:node_pk>', views.node_feedback_view, name='node_feedback_view'),
    path('courses/<course_title>', views.new_course_view, name='new_course_view'),
    path('courses/maps/<course_title>', views.course_map_view, name='course_map_view'),
    path('courses/maps/<course_title>/<uid>', views.course_local_map_view, name='course_local_map_view'),
    path('courses/feedback/<int:course_pk>', views.course_feedback_view, name='course_feedback_view'),
    path('repos/delete/<int:pk>', views.DeleteRepoView.as_view(), name='delete_repo_view'),
    path('notifications/', include("pinax.notifications.urls",namespace="pinax_notifications")),
]
