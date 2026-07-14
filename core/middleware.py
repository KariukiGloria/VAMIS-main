import time
from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect

EXEMPT_URLS = ['/login/', '/logout/']
INACTIVITY_TIMEOUT = getattr(settings, 'SESSION_INACTIVITY_TIMEOUT', 900)


class InactivityLogoutMiddleware:
    """
    Logs out the user after SESSION_INACTIVITY_TIMEOUT seconds of inactivity.
    Every authenticated request updates the last_activity timestamp in the session.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            path = request.path_info
            if path not in EXEMPT_URLS:
                now = time.time()
                last = request.session.get('last_activity')
                if last and (now - last) > INACTIVITY_TIMEOUT:
                    logout(request)
                    from django.contrib import messages
                    messages.warning(
                        request,
                        'You were logged out due to inactivity. Please log in again.'
                    )
                    return redirect(f'/login/?next={path}')
                request.session['last_activity'] = now

        return self.get_response(request)
