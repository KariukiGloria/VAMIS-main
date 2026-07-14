from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def permission_required(perm):
    """
    Usage: @permission_required('can_view_reports')
    Admin always passes. Patient is always blocked (they use the portal).
    For health_worker and distributor, checks UserPermission.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = request.user
            # Admin bypasses all permission checks
            if user.is_admin:
                return view_func(request, *args, **kwargs)
            # Patients never access staff views
            if user.is_patient:
                messages.error(request, 'Access denied.')
                return redirect('patient_portal')
            # Check granular permission
            try:
                perms = user.permissions_profile
            except Exception:
                from .models import UserPermission
                perms = UserPermission.get_or_create_for(user)
            if not getattr(perms, perm, False):
                messages.error(
                    request,
                    'You do not have permission to access this feature. '
                    'Contact your administrator.'
                )
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
