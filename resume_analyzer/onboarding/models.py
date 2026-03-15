"""
Onboarding — UserProfile and step tracking.
Extends Django's User with dev-specific profile data collected during onboarding.
"""
from django.contrib.auth.models import User
from django.db import models

STEP_ORDER = [
    'welcome',
    'personal',
    'roles',
    'skills',
    'experience',
    'resume',
    'assessment',
    'complete',
]

EXPERIENCE_CHOICES = [
    ('0', 'No professional experience'),
    ('0-1', 'Less than 1 year'),
    ('1-2', '1–2 years'),
    ('2-4', '2–4 years'),
    ('4+', '4+ years'),
]

REMOTE_CHOICES = [
    ('remote', 'Remote only'),
    ('hybrid', 'Hybrid'),
    ('onsite', 'On-site'),
    ('flexible', 'Any / flexible'),
]


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    # Personal
    display_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    location = models.CharField(max_length=200, blank=True)
    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)

    # Target roles
    target_titles = models.JSONField(default=list)
    remote_preference = models.CharField(max_length=20, choices=REMOTE_CHOICES, default='remote')
    min_salary = models.IntegerField(default=60000)
    max_experience_years = models.IntegerField(default=4)

    # Skills (populated during onboarding)
    known_skills = models.JSONField(default=list)         # list of skill strings
    skill_levels = models.JSONField(default=dict)         # {skill: "beginner|intermediate|advanced"}

    # Experience
    experience_years = models.CharField(max_length=10, choices=EXPERIENCE_CHOICES, default='0-1')
    education_level = models.CharField(max_length=100, blank=True)
    projects_summary = models.TextField(blank=True)

    # Onboarding state
    onboarding_completed = models.BooleanField(default=False)
    current_step = models.CharField(max_length=20, default='welcome')
    onboarding_started_at = models.DateTimeField(auto_now_add=True)
    onboarding_completed_at = models.DateTimeField(null=True, blank=True)

    # Assessment result from onboarding
    onboarding_assessment_level = models.CharField(max_length=20, blank=True)
    onboarding_assessment_score = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.username} profile'

    def next_step(self) -> str:
        try:
            idx = STEP_ORDER.index(self.current_step)
            return STEP_ORDER[idx + 1] if idx + 1 < len(STEP_ORDER) else 'complete'
        except ValueError:
            return 'welcome'

    def step_number(self) -> int:
        try:
            return STEP_ORDER.index(self.current_step) + 1
        except ValueError:
            return 1

    def step_total(self) -> int:
        return len(STEP_ORDER)

    def progress_percent(self) -> int:
        return round((self.step_number() / self.step_total()) * 100)
