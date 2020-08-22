from django.urls import path
from django.conf.urls import include

from . import views, contentviews

app_name = 'checkerapp'
urlpatterns = [
    path('', views.index_view, name='index'),
    path('create_repo', views.CreateRepoView.as_view(), name='create_repo'),
    path('content/impossible_node', contentviews.ImpossibleNodeView.as_view(), name=f'{contentviews.ImpossibleNodeView.uid}_view'),
    path('courses/<course_title>', views.new_course_view, name='new_course_view'),
    path('repos/delete/<int:pk>', views.DeleteRepoView.as_view(), name='delete_repo_view'),
]
