from django.urls import path
from . import views

urlpatterns = [
    path('', views.resume_list, name='resume_list'),
    path('upload/', views.resume_upload, name='resume_upload'),
    path('<int:pk>/', views.resume_detail, name='resume_detail'),
    path('<int:pk>/delete/', views.resume_delete, name='resume_delete'),
    path('<int:pk>/match/', views.job_match, name='job_match'),
    path('builder/', views.resume_builder, name='resume_builder'),
]
