from django.contrib import admin
from .models import Company, JobApplication, InterviewNote

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'priority', 'updated_at']
    list_filter = ['status', 'priority']

admin.site.register(JobApplication)
admin.site.register(InterviewNote)
