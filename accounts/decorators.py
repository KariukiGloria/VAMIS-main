from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def permission_required(perm):
    """
    Check UserPermission for health workers / distributors.
    Admins always pass through.
    Patients are always redirected to their portal.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            user = request.user
            if user.is_admin:
                return view_func(request, *args, **kwargs)
            if user.is_patient:
                messages.error(request, 'Access denied.')
                return redirect('patient_portal')
            try:
                perms = user.permissions_profile
                if not getattr(perms, perm, False):
                    messages.error(
                        request,
                        'You do not have permission to perform this action.'
                    )
                    return redirect('dashboard')
            except Exception:
                messages.error(
                    request,
                    'Your account has no permissions configured. '
                    'Please contact an administrator.'
                )
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator
