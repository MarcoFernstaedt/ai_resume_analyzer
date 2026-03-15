"""Claude AI-powered resume analysis service."""
import json
import logging
import os

import anthropic

logger = logging.getLogger(__name__)

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get('ANTHROPIC_API_KEY', '')
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def analyze_resume(text: str) -> dict:
    """
    Full AI analysis of a resume. Returns structured feedback dict.
    """
    client = _get_client()

    prompt = f"""You are an expert technical recruiter and career coach specializing in junior developer resumes.

Analyze the following resume and return a JSON object with this exact structure:
{{
  "score": <integer 0-100>,
  "experience_years": <float>,
  "education_level": "<string: high_school|bootcamp|associate|bachelor|master|phd>",
  "skills": ["skill1", "skill2", ...],
  "skill_categories": {{
    "languages": ["Python", "JavaScript", ...],
    "frameworks": ["React", "Django", ...],
    "databases": ["PostgreSQL", "MongoDB", ...],
    "tools": ["Git", "Docker", ...],
    "cloud": ["AWS", "GCP", ...]
  }},
  "strengths": ["strength1", "strength2", ...],
  "weaknesses": ["weakness1", "weakness2", ...],
  "critical_issues": ["issue1", ...],
  "quick_wins": ["fix1", "fix2", ...],
  "sections": {{
    "summary": {{"present": true/false, "score": 0-10, "feedback": "..."}},
    "experience": {{"present": true/false, "score": 0-10, "feedback": "..."}},
    "education": {{"present": true/false, "score": 0-10, "feedback": "..."}},
    "skills": {{"present": true/false, "score": 0-10, "feedback": "..."}},
    "projects": {{"present": true/false, "score": 0-10, "feedback": "..."}},
    "links": {{"present": true/false, "score": 0-10, "feedback": "..."}}
  }},
  "ats_score": <integer 0-100>,
  "ats_issues": ["issue1", ...],
  "impact_score": <integer 0-100>,
  "readability_score": <integer 0-100>,
  "overall_feedback": "<2-3 sentence summary>",
  "top_improvement": "<single most important thing to fix>",
  "seniority_assessment": "<beginner|junior|mid|senior>",
  "recommended_roles": ["Role 1", "Role 2", "Role 3"]
}}

Resume text:
---
{text[:4000]}
---

Return ONLY the JSON object, no markdown, no explanation."""

    try:
        response = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=2000,
            messages=[{'role': 'user', 'content': prompt}],
        )
        raw = response.content[0].text.strip()
        # Strip markdown code blocks if present
        if raw.startswith('```'):
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]
        return json.loads(raw)
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f'AI analysis error: {e}')
        return _fallback_analysis()


def match_job_description(resume_text: str, job_description: str, job_title: str) -> dict:
    """Match a resume against a job description and return scoring."""
    client = _get_client()

    prompt = f"""You are a technical recruiter. Analyze how well this resume matches the job description.

Return a JSON object:
{{
  "match_score": <integer 0-100>,
  "matching_skills": ["skill1", "skill2", ...],
  "missing_skills": ["skill1", "skill2", ...],
  "nice_to_have_missing": ["skill1", ...],
  "strengths_for_role": ["...", "..."],
  "gaps": ["gap1", "gap2"],
  "cover_letter_angle": "<1 sentence on the best angle for cover letter>",
  "resume_tweaks": ["tweak1", "tweak2", "tweak3"],
  "ai_analysis": "<3-4 sentence detailed analysis>"
}}

Job Title: {job_title}
Job Description:
{job_description[:2000]}

Resume:
{resume_text[:2000]}

Return ONLY valid JSON."""

    try:
        response = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=1500,
            messages=[{'role': 'user', 'content': prompt}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith('```'):
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as e:
        logger.error(f'Job match error: {e}')
        return {'match_score': 0, 'matching_skills': [], 'missing_skills': [], 'ai_analysis': str(e)}


def generate_assessment_questions(tech_stack: list, difficulty: str = 'medium') -> list:
    """Generate skill assessment questions for given tech stack."""
    client = _get_client()

    prompt = f"""You are a senior developer creating a technical interview for a junior developer candidate.

Generate 5 assessment questions for these technologies: {', '.join(tech_stack[:5])}
Difficulty level: {difficulty}

Return a JSON array:
[
  {{
    "question_text": "...",
    "question_type": "multiple_choice|coding|open_ended",
    "difficulty": "easy|medium|hard",
    "category": "<main technology>",
    "options": ["A) ...", "B) ...", "C) ...", "D) ..."],  // only for multiple_choice
    "correct_answer": "...",
    "explanation": "...",
    "max_score": 10
  }},
  ...
]

Make questions practical and relevant to real junior dev work.
For coding questions, provide a small code snippet problem.
Return ONLY valid JSON array."""

    try:
        response = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=2000,
            messages=[{'role': 'user', 'content': prompt}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith('```'):
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as e:
        logger.error(f'Question generation error: {e}')
        return []


def evaluate_answer(question: str, correct_answer: str, user_answer: str, max_score: int = 10) -> dict:
    """Evaluate a user's answer and return score + feedback."""
    client = _get_client()

    prompt = f"""You are a senior developer evaluating a junior developer's answer.

Question: {question}
Expected answer: {correct_answer}
Candidate's answer: {user_answer}

Score the answer and provide constructive feedback.
Return JSON:
{{
  "score": <integer 0-{max_score}>,
  "feedback": "<2-3 sentence constructive feedback>",
  "what_was_right": "<what they got right>",
  "what_to_learn": "<specific concept to study>"
}}

Return ONLY valid JSON."""

    try:
        response = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=500,
            messages=[{'role': 'user', 'content': prompt}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith('```'):
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as e:
        logger.error(f'Answer evaluation error: {e}')
        return {'score': 0, 'feedback': 'Could not evaluate answer.', 'what_was_right': '', 'what_to_learn': ''}


def generate_assessment_summary(questions_data: list) -> dict:
    """Generate final assessment summary with level and recommendations."""
    client = _get_client()
    total = sum(q.get('score', 0) for q in questions_data)
    max_total = sum(q.get('max_score', 10) for q in questions_data)

    prompt = f"""A junior developer just completed a technical assessment.

Results:
Total score: {total}/{max_total}
Questions and scores:
{json.dumps(questions_data, indent=2)[:2000]}

Return JSON:
{{
  "assessed_level": "beginner|junior|mid|senior",
  "overall_score": <integer 0-100>,
  "ai_summary": "<3-4 sentence honest assessment>",
  "recommendations": [
    {{"priority": "high|medium|low", "topic": "...", "resource": "...", "reason": "..."}}
  ],
  "strengths": ["..."],
  "focus_areas": ["..."]
}}

Be honest but encouraging. Tailor advice to junior dev growth.
Return ONLY valid JSON."""

    try:
        response = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=1000,
            messages=[{'role': 'user', 'content': prompt}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith('```'):
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as e:
        logger.error(f'Summary error: {e}')
        return {'assessed_level': 'junior', 'overall_score': 0, 'ai_summary': '', 'recommendations': []}


def research_company(company_name: str, job_title: str = '') -> dict:
    """Generate AI insights about a company for a developer."""
    client = _get_client()

    prompt = f"""You are a career coach helping a junior developer research a company.

Company: {company_name}
Role they're applying for: {job_title or 'Software Developer'}

Provide research insights in JSON format:
{{
  "tech_stack_typical": ["tech1", "tech2", ...],
  "culture_notes": "<2-3 sentences about typical culture>",
  "interview_tips": ["tip1", "tip2", "tip3"],
  "questions_to_ask": ["question1", "question2", "question3"],
  "red_flags_to_watch": ["flag1", "flag2"],
  "preparation_checklist": ["item1", "item2", "item3"],
  "ai_insights": "<2-3 sentences of strategic advice>"
}}

Note: You don't have real-time data, so provide general best practices for researching and interviewing at tech companies.
Return ONLY valid JSON."""

    try:
        response = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=1000,
            messages=[{'role': 'user', 'content': prompt}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith('```'):
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as e:
        logger.error(f'Company research error: {e}')
        return {'tech_stack_typical': [], 'culture_notes': '', 'interview_tips': [], 'ai_insights': str(e)}


def _fallback_analysis() -> dict:
    return {
        'score': 0,
        'experience_years': 0,
        'education_level': 'unknown',
        'skills': [],
        'skill_categories': {'languages': [], 'frameworks': [], 'databases': [], 'tools': [], 'cloud': []},
        'strengths': [],
        'weaknesses': ['Could not analyze resume'],
        'critical_issues': [],
        'quick_wins': [],
        'sections': {},
        'ats_score': 0,
        'ats_issues': [],
        'impact_score': 0,
        'readability_score': 0,
        'overall_feedback': 'Analysis failed. Please try again.',
        'top_improvement': 'Reupload your resume',
        'seniority_assessment': 'junior',
        'recommended_roles': [],
    }
