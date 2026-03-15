import json
from django.db import models


class Resume(models.Model):
    TEMPLATE_CHOICES = [
        ('harvard', 'Harvard'),
        ('google', 'Google'),
        ('minimal', 'Minimal'),
    ]
    STATUS_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('analyzing', 'Analyzing'),
        ('analyzed', 'Analyzed'),
        ('error', 'Error'),
    ]

    file = models.FileField(upload_to='resumes/', blank=True, null=True)
    original_filename = models.CharField(max_length=255, blank=True)
    extracted_text = models.TextField(blank=True)
    skills = models.JSONField(default=list)
    experience_years = models.FloatField(default=0)
    education_level = models.CharField(max_length=100, blank=True)
    feedback = models.JSONField(default=dict)
    score = models.IntegerField(default=0)
    template = models.CharField(max_length=20, choices=TEMPLATE_CHOICES, default='harvard')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f'Resume #{self.id} - {self.original_filename or "Untitled"}'

    @property
    def skills_list(self):
        if isinstance(self.skills, list):
            return self.skills
        return []

    @property
    def score_color(self):
        if self.score >= 80:
            return 'green'
        if self.score >= 60:
            return 'yellow'
        return 'red'


class ResumeSection(models.Model):
    SECTION_TYPES = [
        ('summary', 'Professional Summary'),
        ('experience', 'Work Experience'),
        ('education', 'Education'),
        ('skills', 'Skills'),
        ('projects', 'Projects'),
        ('certifications', 'Certifications'),
        ('links', 'Links & Profiles'),
    ]

    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='sections')
    section_type = models.CharField(max_length=20, choices=SECTION_TYPES)
    content = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.resume} - {self.section_type}'


class JobMatch(models.Model):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='job_matches')
    job_title = models.CharField(max_length=200)
    job_description = models.TextField()
    match_score = models.IntegerField(default=0)
    matching_skills = models.JSONField(default=list)
    missing_skills = models.JSONField(default=list)
    ai_analysis = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-match_score']

    def __str__(self):
        return f'{self.resume} → {self.job_title} ({self.match_score}%)'
