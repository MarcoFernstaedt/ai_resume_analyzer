from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UserProfile

COMMON_TITLES = [
    ('Frontend Developer', 'Frontend Developer'),
    ('Full Stack Developer', 'Full Stack Developer'),
    ('React Developer', 'React Developer'),
    ('JavaScript Developer', 'JavaScript Developer'),
    ('Software Engineer', 'Software Engineer'),
    ('Web Developer', 'Web Developer'),
    ('Backend Developer', 'Backend Developer'),
    ('Node.js Developer', 'Node.js Developer'),
    ('Python Developer', 'Python Developer'),
    ('Mobile Developer', 'Mobile Developer'),
    ('DevOps Engineer', 'DevOps Engineer'),
]

TECH_SKILLS = [
    # Languages
    ('JavaScript', 'JavaScript'), ('TypeScript', 'TypeScript'), ('Python', 'Python'),
    ('Java', 'Java'), ('Go', 'Go'), ('Rust', 'Rust'), ('C#', 'C#'), ('PHP', 'PHP'),
    ('HTML', 'HTML'), ('CSS', 'CSS'),
    # Frontend
    ('React', 'React'), ('Next.js', 'Next.js'), ('Vue.js', 'Vue.js'), ('Angular', 'Angular'),
    ('Svelte', 'Svelte'), ('Tailwind CSS', 'Tailwind CSS'), ('Redux', 'Redux'),
    # Backend
    ('Node.js', 'Node.js'), ('Express', 'Express'), ('Django', 'Django'), ('FastAPI', 'FastAPI'),
    ('Spring Boot', 'Spring Boot'), ('Laravel', 'Laravel'),
    # Databases
    ('PostgreSQL', 'PostgreSQL'), ('MySQL', 'MySQL'), ('MongoDB', 'MongoDB'), ('Redis', 'Redis'),
    ('SQLite', 'SQLite'), ('Firebase', 'Firebase'),
    # Cloud / DevOps
    ('AWS', 'AWS'), ('GCP', 'GCP'), ('Azure', 'Azure'), ('Docker', 'Docker'),
    ('Kubernetes', 'Kubernetes'), ('CI/CD', 'CI/CD'), ('Linux', 'Linux'),
    # Tools
    ('Git', 'Git'), ('GraphQL', 'GraphQL'), ('REST APIs', 'REST APIs'),
    ('WebSockets', 'WebSockets'), ('Socket.io', 'Socket.io'),
]


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'autocomplete': 'email'}))
    first_name = forms.CharField(max_length=50, required=True)

    class Meta:
        model = User
        fields = ('first_name', 'email', 'username', 'password1', 'password2')


class PersonalInfoForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('display_name', 'phone', 'location', 'linkedin_url', 'github_url')
        widgets = {
            'display_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Jane Developer'}),
            'phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+1 (555) 000-0000'}),
            'location': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Phoenix, AZ'}),
            'linkedin_url': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://linkedin.com/in/jane'}),
            'github_url': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://github.com/jane'}),
        }


class RolesForm(forms.ModelForm):
    target_titles = forms.MultipleChoiceField(
        choices=COMMON_TITLES,
        widget=forms.CheckboxSelectMultiple,
        required=True,
    )

    class Meta:
        model = UserProfile
        fields = ('target_titles', 'remote_preference', 'min_salary', 'max_experience_years')
        widgets = {
            'min_salary': forms.NumberInput(attrs={'min': 0, 'step': 5000}),
            'max_experience_years': forms.NumberInput(attrs={'min': 0, 'max': 10}),
        }


class ExperienceForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('experience_years', 'education_level', 'projects_summary')
        widgets = {
            'experience_years': forms.Select(attrs={'class': 'form-input'}),
            'education_level': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'B.S. Computer Science, Mesa CC...'}),
            'projects_summary': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 4,
                'placeholder': 'Briefly describe your 1-2 strongest projects...',
            }),
        }
