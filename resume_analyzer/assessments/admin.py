from django.contrib import admin
from .models import SkillAssessment, AssessmentQuestion, TechCategory

admin.site.register(TechCategory)
admin.site.register(SkillAssessment)
admin.site.register(AssessmentQuestion)
