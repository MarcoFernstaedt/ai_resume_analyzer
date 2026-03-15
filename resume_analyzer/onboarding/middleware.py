"""
Onboarding middleware — redirects authenticated users who haven't completed
onboarding to the current onboarding step.
"""
from django.shortcuts import redirect
from django.urls import reverse

EXEMPT_PREFIXES = (
    '/accounts/',
    '/auth/',
    '/onboarding/',
    '/admin/',
    '/static/',
    '/media/',
    '/favicon',
)


class OnboardingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and not any(request.path.startswith(p) for p in EXEMPT_PREFIXES)
        ):
            try:
                profile = request.user.profile
                if not profile.onboarding_completed:
                    onboarding_url = reverse('onboarding_step', kwargs={'step': profile.current_step})
                    if request.path != onboarding_url:
                        return redirect(onboarding_url)
            except Exception:
                pass

        return self.get_response(request)
