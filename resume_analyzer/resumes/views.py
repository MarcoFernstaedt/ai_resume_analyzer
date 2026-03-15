import json
import os
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Resume, ResumeSection, JobMatch
from .services.parser import parse_resume
from .services.ai_analyzer import analyze_resume, match_job_description
from .services.exporter import export_harvard_template, export_google_template, export_plain_text


@login_required
def dashboard(request):
    resumes = Resume.objects.all()[:5]
    total_resumes = Resume.objects.count()
    from companies.models import Company, JobApplication
    from assessments.models import SkillAssessment
    total_companies = Company.objects.count()
    total_applications = JobApplication.objects.count()
    total_assessments = SkillAssessment.objects.count()
    context = {
        'resumes': resumes,
        'total_resumes': total_resumes,
        'total_companies': total_companies,
        'total_applications': total_applications,
        'total_assessments': total_assessments,
    }
    return render(request, 'dashboard.html', context)


@login_required
def resume_upload(request):
    if request.method == 'POST':
        uploaded_file = request.FILES.get('resume_file')
        if not uploaded_file:
            messages.error(request, 'Please select a file to upload.')
            return render(request, 'resumes/upload.html')

        allowed = {'.pdf', '.docx', '.txt'}
        ext = os.path.splitext(uploaded_file.name)[1].lower()
        if ext not in allowed:
            messages.error(request, f'Unsupported file type. Please upload PDF, DOCX, or TXT.')
            return render(request, 'resumes/upload.html')

        try:
            text = parse_resume(uploaded_file)
        except ValueError as e:
            messages.error(request, str(e))
            return render(request, 'resumes/upload.html')

        resume = Resume.objects.create(
            file=uploaded_file,
            original_filename=uploaded_file.name,
            extracted_text=text,
            status='analyzing',
        )

        try:
            analysis = analyze_resume(text)
            resume.skills = analysis.get('skills', [])
            resume.experience_years = analysis.get('experience_years', 0)
            resume.education_level = analysis.get('education_level', '')
            resume.feedback = analysis
            resume.score = analysis.get('score', 0)
            resume.status = 'analyzed'
            resume.save()
        except Exception as e:
            resume.status = 'error'
            resume.save()
            messages.error(request, f'Analysis failed: {e}')
            return redirect('resume_detail', pk=resume.pk)

        return redirect('resume_detail', pk=resume.pk)

    return render(request, 'resumes/upload.html')


@login_required
def resume_list(request):
    resumes = Resume.objects.all()
    return render(request, 'resumes/list.html', {'resumes': resumes})


@login_required
def resume_detail(request, pk):
    resume = get_object_or_404(Resume, pk=pk)
    feedback = resume.feedback or {}
    job_matches = resume.job_matches.all()[:5]
    context = {
        'resume': resume,
        'feedback': feedback,
        'job_matches': job_matches,
        'skill_categories': feedback.get('skill_categories', {}),
        'sections': feedback.get('sections', {}),
    }
    return render(request, 'resumes/detail.html', context)


@login_required
def resume_delete(request, pk):
    resume = get_object_or_404(Resume, pk=pk)
    if request.method == 'POST':
        resume.delete()
        messages.success(request, 'Resume deleted.')
        return redirect('resume_list')
    return render(request, 'resumes/confirm_delete.html', {'resume': resume})


@login_required
@require_http_methods(['POST'])
def job_match(request, pk):
    resume = get_object_or_404(Resume, pk=pk)
    job_title = request.POST.get('job_title', '')
    job_description = request.POST.get('job_description', '')

    if not job_description:
        messages.error(request, 'Please provide a job description.')
        return redirect('resume_detail', pk=pk)

    result = match_job_description(resume.extracted_text, job_description, job_title)
    JobMatch.objects.create(
        resume=resume,
        job_title=job_title,
        job_description=job_description,
        match_score=result.get('match_score', 0),
        matching_skills=result.get('matching_skills', []),
        missing_skills=result.get('missing_skills', []),
        ai_analysis=result.get('ai_analysis', ''),
    )
    return redirect('resume_detail', pk=pk)


@login_required
def resume_builder(request):
    """Interactive resume builder with AI guidance."""
    resume_id = request.GET.get('resume_id')
    resume = None
    if resume_id:
        resume = Resume.objects.filter(pk=resume_id).first()

    if request.method == 'POST':
        resume_data = {
            'name': request.POST.get('name', ''),
            'email': request.POST.get('email', ''),
            'phone': request.POST.get('phone', ''),
            'location': request.POST.get('location', ''),
            'linkedin': request.POST.get('linkedin', ''),
            'github': request.POST.get('github', ''),
            'summary': request.POST.get('summary', ''),
            'skills': [s.strip() for s in request.POST.get('skills', '').split(',') if s.strip()],
        }

        # Parse experience entries
        exp_titles = request.POST.getlist('exp_title[]')
        exp_companies = request.POST.getlist('exp_company[]')
        exp_dates = request.POST.getlist('exp_dates[]')
        exp_bullets = request.POST.getlist('exp_bullets[]')
        resume_data['experience'] = [
            {'title': t, 'company': c, 'dates': d, 'bullets': [b.strip() for b in bul.split('\n') if b.strip()]}
            for t, c, d, bul in zip(exp_titles, exp_companies, exp_dates, exp_bullets)
        ]

        # Education
        edu_degrees = request.POST.getlist('edu_degree[]')
        edu_schools = request.POST.getlist('edu_school[]')
        edu_dates = request.POST.getlist('edu_dates[]')
        resume_data['education'] = [
            {'degree': d, 'school': s, 'dates': dt}
            for d, s, dt in zip(edu_degrees, edu_schools, edu_dates)
        ]

        # Projects
        proj_names = request.POST.getlist('proj_name[]')
        proj_descs = request.POST.getlist('proj_desc[]')
        proj_techs = request.POST.getlist('proj_tech[]')
        resume_data['projects'] = [
            {'name': n, 'description': d, 'tech': t}
            for n, d, t in zip(proj_names, proj_descs, proj_techs)
        ]

        template = request.POST.get('template', 'harvard')
        request.session['builder_data'] = resume_data

        if 'export_docx' in request.POST:
            if template == 'google':
                docx_bytes = export_google_template(resume_data)
            else:
                docx_bytes = export_harvard_template(resume_data)
            response = HttpResponse(docx_bytes, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
            response['Content-Disposition'] = f'attachment; filename="{resume_data["name"].replace(" ", "_")}_resume.docx"'
            return response

        if 'export_txt' in request.POST:
            txt = export_plain_text(resume_data)
            response = HttpResponse(txt, content_type='text/plain')
            response['Content-Disposition'] = f'attachment; filename="{resume_data["name"].replace(" ", "_")}_resume.txt"'
            return response

        return render(request, 'resumes/builder.html', {'resume_data': resume_data, 'resume': resume, 'saved': True})

    saved_data = request.session.get('builder_data', {})
    return render(request, 'resumes/builder.html', {'resume_data': saved_data, 'resume': resume})
