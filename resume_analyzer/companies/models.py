from django.db import models


class Company(models.Model):
    STATUS_CHOICES = [
        ('researching', 'Researching'),
        ('applied', 'Applied'),
        ('interviewing', 'Interviewing'),
        ('offer', 'Offer Received'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('dream', 'Dream Company'),
    ]

    name = models.CharField(max_length=200)
    website = models.URLField(blank=True)
    industry = models.CharField(max_length=100, blank=True)
    size = models.CharField(max_length=50, blank=True)
    location = models.CharField(max_length=200, blank=True)
    remote_policy = models.CharField(max_length=50, blank=True)
    tech_stack = models.JSONField(default=list)
    culture_notes = models.TextField(blank=True)
    glassdoor_rating = models.FloatField(null=True, blank=True)
    ai_insights = models.TextField(blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='researching')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Companies'
        ordering = ['-updated_at']

    def __str__(self):
        return self.name

    @property
    def status_color(self):
        colors = {
            'researching': 'blue',
            'applied': 'yellow',
            'interviewing': 'purple',
            'offer': 'green',
            'rejected': 'red',
            'withdrawn': 'gray',
        }
        return colors.get(self.status, 'gray')


class JobApplication(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='applications')
    resume = models.ForeignKey('resumes.Resume', on_delete=models.SET_NULL, null=True, blank=True)
    job_title = models.CharField(max_length=200)
    job_url = models.URLField(blank=True)
    job_description = models.TextField(blank=True)
    salary_min = models.IntegerField(null=True, blank=True)
    salary_max = models.IntegerField(null=True, blank=True)
    applied_date = models.DateField(null=True, blank=True)
    follow_up_date = models.DateField(null=True, blank=True)
    cover_letter = models.TextField(blank=True)
    ai_tailoring_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.company.name} - {self.job_title}'


class InterviewNote(models.Model):
    ROUND_CHOICES = [
        ('phone_screen', 'Phone Screen'),
        ('technical', 'Technical'),
        ('system_design', 'System Design'),
        ('behavioral', 'Behavioral'),
        ('final', 'Final Round'),
    ]

    application = models.ForeignKey(JobApplication, on_delete=models.CASCADE, related_name='interview_notes')
    round_type = models.CharField(max_length=20, choices=ROUND_CHOICES)
    date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    questions_asked = models.JSONField(default=list)
    outcome = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date']

    def __str__(self):
        return f'{self.application} - {self.round_type}'
