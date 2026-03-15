import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages

from .models import SkillAssessment, AssessmentQuestion, TechCategory
from resumes.services.ai_analyzer import (
    generate_assessment_questions,
    evaluate_answer,
    generate_assessment_summary,
)

COMMON_TECH = [
    'JavaScript', 'TypeScript', 'Python', 'Java', 'Go', 'Rust', 'C++',
    'React', 'Vue', 'Angular', 'Next.js', 'Svelte',
    'Node.js', 'Express', 'Django', 'FastAPI', 'Spring Boot',
    'PostgreSQL', 'MySQL', 'MongoDB', 'Redis',
    'Docker', 'Kubernetes', 'AWS', 'GCP', 'Azure',
    'Git', 'Linux', 'GraphQL', 'REST APIs',
    'HTML', 'CSS', 'Tailwind CSS',
]


@login_required
def assessment_list(request):
    assessments = SkillAssessment.objects.all()
    return render(request, 'assessments/list.html', {'assessments': assessments})


@login_required
def assessment_start(request):
    if request.method == 'POST':
        tech_stack = request.POST.getlist('tech_stack')
        if not tech_stack:
            messages.error(request, 'Please select at least one technology.')
            return render(request, 'assessments/start.html', {'tech_list': COMMON_TECH})

        resume_id = request.POST.get('resume_id')
        from resumes.models import Resume
        resume = Resume.objects.filter(pk=resume_id).first() if resume_id else None

        assessment = SkillAssessment.objects.create(
            resume=resume,
            tech_stack=tech_stack,
            status='in_progress',
        )

        # Generate questions
        questions_data = generate_assessment_questions(tech_stack)
        for i, q in enumerate(questions_data):
            cat, _ = TechCategory.objects.get_or_create(
                slug=q.get('category', 'general').lower().replace(' ', '-'),
                defaults={'name': q.get('category', 'General')},
            )
            AssessmentQuestion.objects.create(
                assessment=assessment,
                category=cat,
                question_text=q.get('question_text', ''),
                question_type=q.get('question_type', 'open_ended'),
                difficulty=q.get('difficulty', 'medium'),
                options=q.get('options', []),
                correct_answer=q.get('correct_answer', ''),
                max_score=q.get('max_score', 10),
                order=i,
            )

        return redirect('assessment_take', pk=assessment.pk)

    from resumes.models import Resume
    resumes = Resume.objects.filter(status='analyzed')
    return render(request, 'assessments/start.html', {'tech_list': COMMON_TECH, 'resumes': resumes})


@login_required
def assessment_take(request, pk):
    assessment = get_object_or_404(SkillAssessment, pk=pk)
    questions = assessment.questions.all()

    if request.method == 'POST':
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

        # Generate summary
        q_data = [
            {
                'question': q.question_text,
                'score': q.score,
                'max_score': q.max_score,
                'feedback': q.ai_feedback,
            }
            for q in questions
        ]
        summary = generate_assessment_summary(q_data)
        assessment.assessed_level = summary.get('assessed_level', 'junior')
        assessment.overall_score = summary.get('overall_score', 0)
        assessment.ai_summary = summary.get('ai_summary', '')
        assessment.recommendations = summary.get('recommendations', [])
        assessment.status = 'completed'
        assessment.completed_at = timezone.now()
        assessment.save()

        return redirect('assessment_result', pk=assessment.pk)

    return render(request, 'assessments/take.html', {'assessment': assessment, 'questions': questions})


@login_required
def assessment_result(request, pk):
    assessment = get_object_or_404(SkillAssessment, pk=pk)
    questions = assessment.questions.all()
    total_score = sum(q.score for q in questions)
    max_score = sum(q.max_score for q in questions)
    context = {
        'assessment': assessment,
        'questions': questions,
        'total_score': total_score,
        'max_score': max_score,
        'percentage': round((total_score / max_score * 100) if max_score else 0),
    }
    return render(request, 'assessments/result.html', context)


@login_required
def assessment_detail(request, pk):
    assessment = get_object_or_404(SkillAssessment, pk=pk)
    if assessment.status == 'in_progress':
        return redirect('assessment_take', pk=pk)
    return redirect('assessment_result', pk=pk)
