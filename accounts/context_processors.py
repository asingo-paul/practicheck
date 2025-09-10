# accounts/context_processors.py
def user_type(request):
    return {
        'user_type': request.user.user_type if request.user.is_authenticated else None,
        'user_type_display': request.user.get_user_type_display() if request.user.is_authenticated else None,
    }