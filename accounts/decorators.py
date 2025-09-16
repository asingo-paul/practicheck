from functools import wraps
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.contrib import messages

def role_required(allowed_roles):
    """
    Decorator to restrict view access to users with specific roles.
    allowed_roles should be a list of integers, e.g. [1, 2].
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                return redirect('accounts:login')

            try:
                user_type = int(user.user_type)  #always cast
            except (ValueError, TypeError):
                return HttpResponseForbidden("Invalid user type.")

            if user_type in allowed_roles:
                return view_func(request, *args, **kwargs)
            return HttpResponseForbidden("You do not have permission to view this page.")
        return _wrapped_view
    return decorator
# accounts/decorators.py - add this decorator
def supervisor_required(view_func):
    """
    Decorator for views that checks that the user is a supervisor (role=2),
    redirecting to the login page if necessary.
    """
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)
        
        if not hasattr(request.user, 'role') or request.user.role != 2:
            messages.error(request, "You don't have permission to access this page.")
            return redirect('accounts:profile')  # Or wherever you want to redirect
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view