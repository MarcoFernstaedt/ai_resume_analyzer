from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('step/<str:step>/', views.onboarding_step, name='onboarding_step'),
    path('', views.onboarding_step, {'step': 'welcome'}, name='onboarding_home'),
]
