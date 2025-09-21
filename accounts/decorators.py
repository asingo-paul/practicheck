from functools import wraps
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.conf import settings

def role_required(allowed_roles):
    """
    Restrict view access to users with specific roles.
    Example: @role_required([2, 3])  # allows supervisors & lecturers
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(settings.LOGIN_URL)

            # pick whichever field you actually use (role or user_type)
            user_role = getattr(request.user, "role", None) or getattr(request.user, "user_type", None)

            try:
                user_role = int(user_role)
            except (ValueError, TypeError):
                raise PermissionDenied("Invalid role")

            if user_role not in allowed_roles:
                raise PermissionDenied("You do not have permission to view this page.")

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def supervisor_required(view_func):
    """Shortcut → only supervisors (role=2)"""
    return role_required([2])(view_func)


def lecturer_required(view_func):
    """Shortcut → only lecturers (role=3)"""
    return role_required([3])(view_func)
