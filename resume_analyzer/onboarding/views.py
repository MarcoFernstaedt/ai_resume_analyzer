"""
Onboarding views — registration, login/logout, and 8-step onboarding wizard.
"""
import json
import logging
import os
from datetime import datetime

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods

from .forms import RegisterForm, PersonalInfoForm, RolesForm, ExperienceForm, TECH_SKILLS
from .models import UserProfile, STEP_ORDER

logger = logging.getLogger(__name__)

# Steps that require POST to advance
FORM_STEPS = {
    'personal': PersonalInfoForm,
    'roles': RolesForm,
    'experience': ExperienceForm,
}

STEP_META = {
    'welcome':    {'title': 'Welcome',       'subtitle': 'Your dev career starts here',      'icon': '⚡'},
    'personal':   {'title': 'Who Are You?',  'subtitle': 'Tell us about yourself',           'icon': '👤'},
    'roles':      {'title': 'Target Roles',  'subtitle': 'What jobs are you hunting?',       'icon': '🎯'},
    'skills':     {'title': 'Your Stack',    'subtitle': 'What tech do you know?',           'icon': '🛠️'},
    'experience': {'title': 'Experience',    'subtitle': 'Your background',                  'icon': '💼'},
    'resume':     {'title': 'Your Resume',   'subtitle': 'Upload or build from scratch',     'icon': '📄'},
    'assessment': {'title': 'Skill Check',   'subtitle': 'Prove what you know',              'icon': '🧪'},
    'complete':   {'title': 'You\'re Ready', 'subtitle': 'Let\'s land that job',             'icon': '🚀'},
}


# ── Auth ─────────────────────────────────────────────────────────────────────

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save(commit=False)
        user.email = form.cleaned_data['email']
        user.first_name = form.cleaned_data['first_name']
        user.save()
        # Profile created by signal; set display name
        user.profile.display_name = form.cleaned_data['first_name']
        user.profile.save()
        login(request, user)
        return redirect('onboarding_step', step='welcome')

    return render(request, 'auth/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        next_url = request.GET.get('next', '')
        if next_url:
            return redirect(next_url)
        # Check onboarding
        if hasattr(user, 'profile') and not user.profile.onboarding_completed:
            return redirect('onboarding_step', step=user.profile.current_step)
        return redirect('dashboard')

    return render(request, 'auth/login.html', {'form': form})


@require_http_methods(['POST'])
def logout_view(request):
    logout(request)
    return redirect('login')


# ── Onboarding wizard ─────────────────────────────────────────────────────────

@login_required
def onboarding_step(request, step='welcome'):
    profile = request.user.profile

    if profile.onboarding_completed and step != 'complete':
        return redirect('dashboard')

    if step not in STEP_ORDER:
        return redirect('onboarding_step', step=profile.current_step)

    # Don't let users skip ahead
    current_idx = STEP_ORDER.index(profile.current_step)
    requested_idx = STEP_ORDER.index(step)
    if requested_idx > current_idx:
        return redirect('onboarding_step', step=profile.current_step)

    handler = STEP_HANDLERS.get(step, _default_step)
    return handler(request, profile, step)


def _render_step(request, profile, step, extra_ctx=None):
    meta = STEP_META.get(step, {})
    ctx = {
        'step': step,
        'step_number': profile.step_number(),
        'step_total': profile.step_total(),
        'progress_percent': profile.progress_percent(),
        'step_title': meta.get('title', step.title()),
        'step_subtitle': meta.get('subtitle', ''),
        'step_icon': meta.get('icon', ''),
        'profile': profile,
        'next_step': profile.next_step(),
        'step_order': STEP_ORDER,
        **(extra_ctx or {}),
    }
    return render(request, f'onboarding/step_{step}.html', ctx)


def _advance(profile, step):
    """Move profile to the given step."""
    profile.current_step = step
    profile.save()


# ── Step handlers ─────────────────────────────────────────────────────────────

def _step_welcome(request, profile, step):
    if request.method == 'POST':
        _advance(profile, 'personal')
        return redirect('onboarding_step', step='personal')
    return _render_step(request, profile, step)


def _step_personal(request, profile, step):
    form = PersonalInfoForm(request.POST or None, instance=profile)
    if request.method == 'POST' and form.is_valid():
        form.save()
        _advance(profile, 'roles')
        return redirect('onboarding_step', step='roles')
    return _render_step(request, profile, step, {'form': form})


def _step_roles(request, profile, step):
    if request.method == 'POST':
        titles = request.POST.getlist('target_titles')
        remote = request.POST.get('remote_preference', 'remote')
        min_sal = int(request.POST.get('min_salary', 60000) or 60000)
        max_exp = int(request.POST.get('max_experience_years', 4) or 4)
        profile.target_titles = titles
        profile.remote_preference = remote
        profile.min_salary = min_sal
        profile.max_experience_years = max_exp
        profile.current_step = 'skills'
        profile.save()
        return redirect('onboarding_step', step='skills')
    from .forms import COMMON_TITLES
    return _render_step(request, profile, step, {
        'title_choices': COMMON_TITLES,
        'remote_choices': UserProfile._meta.get_field('remote_preference').choices,
    })


def _step_skills(request, profile, step):
    if request.method == 'POST':
        skills = request.POST.getlist('skills')
        levels = {}
        for skill in skills:
            level = request.POST.get(f'level_{skill}', 'beginner')
            levels[skill] = level
        profile.known_skills = skills
        profile.skill_levels = levels
        profile.current_step = 'experience'
        profile.save()
        return redirect('onboarding_step', step='experience')

    # Group skills by category for the UI
    categories = {
        'Languages': ['JavaScript', 'TypeScript', 'Python', 'Java', 'Go', 'Rust', 'C#', 'PHP', 'HTML', 'CSS'],
        'Frontend': ['React', 'Next.js', 'Vue.js', 'Angular', 'Svelte', 'Tailwind CSS', 'Redux'],
        'Backend': ['Node.js', 'Express', 'Django', 'FastAPI', 'Spring Boot', 'Laravel'],
        'Databases': ['PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'SQLite', 'Firebase'],
        'Cloud / DevOps': ['AWS', 'GCP', 'Azure', 'Docker', 'Kubernetes', 'CI/CD', 'Linux'],
        'Tools & APIs': ['Git', 'GraphQL', 'REST APIs', 'WebSockets', 'Socket.io'],
    }
    return _render_step(request, profile, step, {
        'skill_categories': categories,
        'selected_skills': profile.known_skills,
        'skill_levels': profile.skill_levels,
    })


def _step_experience(request, profile, step):
    form = ExperienceForm(request.POST or None, instance=profile)
    if request.method == 'POST' and form.is_valid():
        form.save()
        profile.current_step = 'resume'
        profile.save()
        return redirect('onboarding_step', step='resume')
    return _render_step(request, profile, step, {'form': form})


def _step_resume(request, profile, step):
    if request.method == 'POST':
        if 'resume_file' in request.FILES:
            # Upload and analyze resume
            from resumes.services.parser import parse_resume
            from resumes.services.ai_analyzer import analyze_resume
            from resumes.models import Resume

            uploaded = request.FILES['resume_file']
            try:
                text = parse_resume(uploaded)
                resume = Resume.objects.create(
                    file=uploaded,
                    original_filename=uploaded.name,
                    extracted_text=text,
                    status='analyzing',
                )
                analysis = analyze_resume(text)
                resume.skills = analysis.get('skills', [])
                resume.experience_years = analysis.get('experience_years', 0)
                resume.education_level = analysis.get('education_level', '')
                resume.feedback = analysis
                resume.score = analysis.get('score', 0)
                resume.status = 'analyzed'
                resume.save()

                # Merge extracted skills into profile
                existing = set(profile.known_skills)
                new_skills = [s for s in resume.skills if s not in existing]
                profile.known_skills = list(existing) + new_skills
                profile.current_step = 'assessment'
                profile.save()
                messages.success(request, f'Resume analyzed! Score: {resume.score}%')
            except Exception as e:
                messages.error(request, f'Could not parse resume: {e}')
        else:
            # Skip upload — use questionnaire data
            profile.current_step = 'assessment'
            profile.save()
        return redirect('onboarding_step', step='assessment')

    return _render_step(request, profile, step)


def _step_assessment(request, profile, step):
    from assessments.models import SkillAssessment, AssessmentQuestion, TechCategory
    from resumes.services.ai_analyzer import generate_assessment_questions, evaluate_answer, generate_assessment_summary

    # Use the user's stated skills for the assessment
    tech_stack = profile.known_skills[:5] or ['JavaScript', 'React']

    if request.method == 'POST':
        assessment_id = request.session.get('onboarding_assessment_id')
        if not assessment_id:
            messages.error(request, 'Assessment not found. Please refresh.')
            return redirect('onboarding_step', step='assessment')

        try:
            assessment = SkillAssessment.objects.get(pk=assessment_id)
            questions = assessment.questions.all()

            for question in questions:
                answer_key = f'answer_{question.pk}'
                user_answer = request.POST.get(answer_key, '')
                if user_answer:
                    result = evaluate_answer(
                        question.question_text,
                        question.correct_answer,
                        user_answer,
                        question.max_score,
                    )
                    question.user_answer = user_answer
                    question.score = result.get('score', 0)
                    question.ai_feedback = result.get('feedback', '')
                    question.save()

            q_data = [{'question': q.question_text, 'score': q.score, 'max_score': q.max_score, 'feedback': q.ai_feedback} for q in questions]
            summary = generate_assessment_summary(q_data)

            assessment.assessed_level = summary.get('assessed_level', 'junior')
            assessment.overall_score = summary.get('overall_score', 0)
            assessment.ai_summary = summary.get('ai_summary', '')
            assessment.recommendations = summary.get('recommendations', [])
            assessment.status = 'completed'
            assessment.completed_at = datetime.now()
            assessment.save()

            profile.onboarding_assessment_level = assessment.assessed_level
            profile.onboarding_assessment_score = assessment.overall_score
            profile.current_step = 'complete'
            profile.onboarding_completed = True
            profile.onboarding_completed_at = datetime.now()
            profile.save()

            # Update config.yaml with user's profile
            _sync_config(profile)

            return redirect('onboarding_step', step='complete')
        except Exception as e:
            logger.error(f'Assessment submit error: {e}')
            messages.error(request, 'Assessment error. Skipping to dashboard.')
            profile.current_step = 'complete'
            profile.onboarding_completed = True
            profile.onboarding_completed_at = datetime.now()
            profile.save()
            return redirect('onboarding_step', step='complete')

    # Generate questions if not already done
    assessment_id = request.session.get('onboarding_assessment_id')
    assessment = None

    if assessment_id:
        assessment = SkillAssessment.objects.filter(pk=assessment_id, status='in_progress').first()

    if not assessment:
        try:
            questions_data = generate_assessment_questions(tech_stack, difficulty='easy')
            assessment = SkillAssessment.objects.create(
                tech_stack=tech_stack,
                status='in_progress',
            )
            for i, q in enumerate(questions_data[:3]):  # 3 questions for onboarding
                cat, _ = TechCategory.objects.get_or_create(
                    slug=q.get('category', 'general').lower().replace(' ', '-'),
                    defaults={'name': q.get('category', 'General')},
                )
                AssessmentQuestion.objects.create(
                    assessment=assessment,
                    category=cat,
                    question_text=q.get('question_text', ''),
                    question_type=q.get('question_type', 'open_ended'),
                    difficulty=q.get('difficulty', 'easy'),
                    options=q.get('options', []),
                    correct_answer=q.get('correct_answer', ''),
                    max_score=q.get('max_score', 10),
                    order=i,
                )
            request.session['onboarding_assessment_id'] = assessment.pk
        except Exception as e:
            logger.error(f'Question generation error: {e}')
            # Skip assessment if API fails
            profile.current_step = 'complete'
            profile.onboarding_completed = True
            profile.onboarding_completed_at = datetime.now()
            profile.save()
            return redirect('onboarding_step', step='complete')

    questions = assessment.questions.all() if assessment else []
    return _render_step(request, profile, step, {
        'assessment': assessment,
        'questions': questions,
        'tech_stack': tech_stack,
    })


def _step_complete(request, profile, step):
    from resumes.models import Resume
    latest_resume = Resume.objects.order_by('-uploaded_at').first()
    return _render_step(request, profile, step, {
        'latest_resume': latest_resume,
    })


def _default_step(request, profile, step):
    return _render_step(request, profile, step)


STEP_HANDLERS = {
    'welcome':    _step_welcome,
    'personal':   _step_personal,
    'roles':      _step_roles,
    'skills':     _step_skills,
    'experience': _step_experience,
    'resume':     _step_resume,
    'assessment': _step_assessment,
    'complete':   _step_complete,
}


def _sync_config(profile):
    """Write user's profile data back to config.yaml for JobSniper."""
    import yaml
    from pathlib import Path

    cfg_path = Path(__file__).resolve().parents[2] / 'config.yaml'
    try:
        with open(cfg_path) as f:
            config = yaml.safe_load(f)

        config['profile']['name'] = profile.display_name or profile.user.get_full_name()
        if profile.target_titles:
            config['profile']['target_titles'] = profile.target_titles
        if profile.known_skills:
            config['profile']['must_have_skills'] = profile.known_skills[:3]
            config['profile']['nice_to_have_skills'] = profile.known_skills[3:12]
        if profile.min_salary:
            config['profile']['min_salary'] = profile.min_salary
        config['profile']['remote_preference'] = profile.remote_preference
        config['profile']['max_experience_years'] = profile.max_experience_years

        with open(cfg_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    except Exception as e:
        logger.warning(f'Could not sync config.yaml: {e}')
