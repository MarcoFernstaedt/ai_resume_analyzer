from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Company, JobApplication, InterviewNote
from resumes.services.ai_analyzer import research_company


def company_list(request):
    status_filter = request.GET.get('status', '')
    companies = Company.objects.all()
    if status_filter:
        companies = companies.filter(status=status_filter)

    status_counts = {}
    for status, _ in Company.STATUS_CHOICES:
        status_counts[status] = Company.objects.filter(status=status).count()

    return render(request, 'companies/list.html', {
        'companies': companies,
        'status_filter': status_filter,
        'status_counts': status_counts,
        'status_choices': Company.STATUS_CHOICES,
    })


def company_create(request):
    if request.method == 'POST':
        tech_raw = request.POST.get('tech_stack', '')
        tech = [t.strip() for t in tech_raw.split(',') if t.strip()]
        company = Company.objects.create(
            name=request.POST.get('name', ''),
            website=request.POST.get('website', ''),
            industry=request.POST.get('industry', ''),
            size=request.POST.get('size', ''),
            location=request.POST.get('location', ''),
            remote_policy=request.POST.get('remote_policy', ''),
            tech_stack=tech,
            culture_notes=request.POST.get('culture_notes', ''),
            glassdoor_rating=request.POST.get('glassdoor_rating') or None,
            status=request.POST.get('status', 'researching'),
            priority=request.POST.get('priority', 'medium'),
            notes=request.POST.get('notes', ''),
        )

        if request.POST.get('ai_research'):
            job_title = request.POST.get('ai_job_title', '')
            try:
                insights = research_company(company.name, job_title)
                company.ai_insights = insights.get('ai_insights', '')
                if not tech:
                    company.tech_stack = insights.get('tech_stack_typical', [])
                company.save()
            except Exception:
                pass

        messages.success(request, f'Company "{company.name}" added!')
        return redirect('company_detail', pk=company.pk)

    return render(request, 'companies/form.html', {
        'status_choices': Company.STATUS_CHOICES,
        'priority_choices': Company.PRIORITY_CHOICES,
    })


def company_detail(request, pk):
    company = get_object_or_404(Company, pk=pk)
    applications = company.applications.all()
    return render(request, 'companies/detail.html', {
        'company': company,
        'applications': applications,
    })


def company_edit(request, pk):
    company = get_object_or_404(Company, pk=pk)
    if request.method == 'POST':
        tech_raw = request.POST.get('tech_stack', '')
        company.name = request.POST.get('name', company.name)
        company.website = request.POST.get('website', company.website)
        company.industry = request.POST.get('industry', company.industry)
        company.size = request.POST.get('size', company.size)
        company.location = request.POST.get('location', company.location)
        company.remote_policy = request.POST.get('remote_policy', company.remote_policy)
        company.tech_stack = [t.strip() for t in tech_raw.split(',') if t.strip()]
        company.culture_notes = request.POST.get('culture_notes', company.culture_notes)
        company.glassdoor_rating = request.POST.get('glassdoor_rating') or company.glassdoor_rating
        company.status = request.POST.get('status', company.status)
        company.priority = request.POST.get('priority', company.priority)
        company.notes = request.POST.get('notes', company.notes)
        company.save()
        messages.success(request, 'Company updated!')
        return redirect('company_detail', pk=pk)

    return render(request, 'companies/form.html', {
        'company': company,
        'status_choices': Company.STATUS_CHOICES,
        'priority_choices': Company.PRIORITY_CHOICES,
    })


def company_delete(request, pk):
    company = get_object_or_404(Company, pk=pk)
    if request.method == 'POST':
        company.delete()
        messages.success(request, 'Company removed.')
        return redirect('company_list')
    return render(request, 'companies/confirm_delete.html', {'company': company})


def application_create(request, company_pk):
    company = get_object_or_404(Company, pk=company_pk)
    if request.method == 'POST':
        from resumes.models import Resume
        resume_id = request.POST.get('resume_id')
        resume = Resume.objects.filter(pk=resume_id).first() if resume_id else None
        sal_min = request.POST.get('salary_min')
        sal_max = request.POST.get('salary_max')
        applied = request.POST.get('applied_date')
        follow_up = request.POST.get('follow_up_date')

        app = JobApplication.objects.create(
            company=company,
            resume=resume,
            job_title=request.POST.get('job_title', ''),
            job_url=request.POST.get('job_url', ''),
            job_description=request.POST.get('job_description', ''),
            salary_min=int(sal_min) if sal_min else None,
            salary_max=int(sal_max) if sal_max else None,
            applied_date=applied or None,
            follow_up_date=follow_up or None,
            cover_letter=request.POST.get('cover_letter', ''),
        )

        company.status = 'applied'
        company.save()

        messages.success(request, f'Application to {company.name} logged!')
        return redirect('company_detail', pk=company.pk)

    from resumes.models import Resume
    resumes = Resume.objects.filter(status='analyzed')
    return render(request, 'companies/application_form.html', {
        'company': company,
        'resumes': resumes,
    })


def application_detail(request, pk):
    application = get_object_or_404(JobApplication, pk=pk)
    return render(request, 'companies/application_detail.html', {'application': application})
