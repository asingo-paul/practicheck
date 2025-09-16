from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import (
    UserRegistrationForm, StudentProfileForm, 
    SupervisorProfileForm, LecturerProfileForm, UserLoginForm
)
from .models import StudentProfile, SupervisorProfile, LecturerProfile
from .forms import UserLoginForm
from attachments.models import Attachment
from django.contrib.auth.forms import AuthenticationForm
from attachments.models import Attachment, LogbookEntry
from django.contrib.auth import get_user_model
from django.shortcuts import render

User = get_user_model()

# accounts/views.py
def register(request):
    if request.method == 'POST':
        user_form = UserRegistrationForm(request.POST)
        
        if user_form.is_valid():
            user = user_form.save()
            
            messages.success(request, 'Account created successfully! You can now log in.')
            return redirect('accounts:login')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        user_form = UserRegistrationForm()
    
    return render(request, 'accounts/register.html', {'user_form': user_form})





def user_login(request):
    if request.method == 'POST':
        form = UserLoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            print("DEBUG ========")
            print("username:", user.username)
            print("raw user_type from DB:", repr(user.user_type), type(user.user_type))
            print("is_authenticated:", user.is_authenticated)
            print("================")

            # Explicit cast for safety
            user_type = int(user.user_type)

            if user_type == 1:
                print("Redirecting to student dashboard")
                return redirect('attachments:dashboard')
            elif user_type == 2:
                print("Redirecting to supervisor dashboard")
                return redirect('evaluations:supervisor_dashboard')
            elif user_type == 3:
                print("Redirecting to lecturer dashboard")
                return redirect('evaluations:lecturer_dashboard')
            elif user_type == 4:
                print("Redirecting to admin site")
                return redirect('/admin/')

            # fallback
            print("No match, redirecting home")
            return redirect('home')
        else:
            print("Form invalid:", form.errors)
    else:
        form = UserLoginForm()
    return render(request, 'accounts/login.html', {'form': form})


@login_required
def profile(request):
    user = request.user
    profile = None
    logbook_entries = []
    total_entries = 0
    completion_rate = 0
    
    if hasattr(user, 'student_profile'):
        profile = user.student_profile
        logbook_entries = LogbookEntry.objects.filter(attachment__student=user).order_by('-entry_date')[:5]
        total_entries = LogbookEntry.objects.filter(attachment__student=user).count()
        
        attachments = Attachment.objects.filter(student=user)
        if attachments.exists():
            completion_rate = round(sum(a.progress_percentage for a in attachments) / attachments.count())
    
    elif hasattr(user, 'supervisor_profile'):
        profile = user.supervisor_profile
    elif hasattr(user, 'lecturer_profile'):
        profile = user.lecturer_profile
    
    return render(request, 'accounts/profile.html', {
        'user': user,
        'profile': profile,
        'logbook_entries': logbook_entries,
        'total_entries': total_entries,
        'completion_rate': completion_rate,
    })

@login_required
def upload_profile_picture(request):
    if request.method == "POST" and request.FILES.get("profile_picture"):
        request.user.profile_picture = request.FILES["profile_picture"]
        request.user.save()
        messages.success(request, "Profile picture updated successfully.")
    return redirect("accounts:profile")


def check_username(request):
    username = request.GET.get('username', None)
    is_taken = User.objects.filter(username__iexact=username).exists()
    return JsonResponse({'is_taken': is_taken})


def about(request):
    """
    Renders the About Us page.
    """
    return render(request, 'about.html')