from django.db import models


class TechCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = 'Tech Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class SkillAssessment(models.Model):
    LEVEL_CHOICES = [
        ('beginner', 'Beginner'),
        ('junior', 'Junior'),
        ('mid', 'Mid-Level'),
        ('senior', 'Senior'),
    ]
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('abandoned', 'Abandoned'),
    ]

    resume = models.ForeignKey('resumes.Resume', on_delete=models.SET_NULL, null=True, blank=True, related_name='assessments')
    tech_stack = models.JSONField(default=list)
    assessed_level = models.CharField(max_length=10, choices=LEVEL_CHOICES, blank=True)
    overall_score = models.IntegerField(default=0)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='in_progress')
    ai_summary = models.TextField(blank=True)
    recommendations = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Assessment #{self.id} - {self.assessed_level or "Pending"}'


class AssessmentQuestion(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]
    TYPE_CHOICES = [
        ('multiple_choice', 'Multiple Choice'),
        ('coding', 'Coding Challenge'),
        ('open_ended', 'Open Ended'),
    ]

    assessment = models.ForeignKey(SkillAssessment, on_delete=models.CASCADE, related_name='questions')
    category = models.ForeignKey(TechCategory, on_delete=models.SET_NULL, null=True, blank=True)
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='open_ended')
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium')
    options = models.JSONField(default=list, blank=True)
    correct_answer = models.TextField(blank=True)
    user_answer = models.TextField(blank=True)
    ai_feedback = models.TextField(blank=True)
    score = models.IntegerField(default=0)
    max_score = models.IntegerField(default=10)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'Q{self.order}: {self.question_text[:60]}...'
