from django.contrib import admin
from .models import Resume, ResumeSection, JobMatch

@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ['id', 'original_filename', 'score', 'status', 'uploaded_at']
    list_filter = ['status', 'template']
    search_fields = ['original_filename']

admin.site.register(ResumeSection)
admin.site.register(JobMatch)
