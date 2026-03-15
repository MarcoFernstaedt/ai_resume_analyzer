from django.urls import path
from . import views

urlpatterns = [
    path('', views.queue_view, name='snipe_queue'),
    path('job/<int:job_id>/', views.detail_view, name='snipe_detail'),
    path('job/<int:job_id>/apply/', views.apply_view, name='snipe_apply'),
    path('job/<int:job_id>/skip/', views.skip_view, name='snipe_skip'),
    path('job/<int:job_id>/regenerate/', views.regenerate_view, name='snipe_regenerate'),
    path('stats/', views.stats_view, name='snipe_stats'),
    path('pipeline/', views.trigger_pipeline, name='snipe_pipeline'),
]
