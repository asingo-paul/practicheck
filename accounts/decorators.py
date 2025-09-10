from functools import wraps
from django.http import HttpResponseForbidden
from django.shortcuts import redirect

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
