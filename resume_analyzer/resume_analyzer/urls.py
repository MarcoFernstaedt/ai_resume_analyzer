from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from resumes.views import dashboard

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', dashboard, name='dashboard'),
    path('resumes/', include('resumes.urls')),
    path('assessments/', include('assessments.urls')),
    path('companies/', include('companies.urls')),
    path('snipe/', include('jobsniper.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
