from django.db import models

# Create your models here.
class Resume(models.Model):
    file = models.FileField(upload_to='resume/')
    extracted_text = modes.TextField(blank=True, null=True)
    skills = modes.TextField(blank=True, null=True)
    feedback = modes.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f'Resume {self.id} - {self.file.name}'