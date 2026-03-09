from django.urls import path
from . import views

urlpatterns = [
    path('', views.SocialTaskListView.as_view(), name='social-tasks-list'),
    path('my-tasks/', views.UserSocialTaskView.as_view(), name='user-social-tasks')
]
