from .models import UserPermission


def user_permissions(request):
    if not request.user.is_authenticated or request.user.is_patient or request.user.is_admin:
        return {'user_perms': None}
    try:
        perms = request.user.permissions_profile
    except Exception:
        perms = UserPermission.get_or_create_for(request.user)
    return {'user_perms': perms}
