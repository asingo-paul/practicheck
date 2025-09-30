# accounts/views.py - Updated version
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .forms import UserRegistrationForm, UserLoginForm
from .models import StudentProfile, SupervisorProfile, LecturerProfile
from django.contrib.auth import get_user_model
from attachments.models import Attachment, LogbookEntry, PlacementFormSubmission, Lecturer

User = get_user_model()

# Updated ROLE_MAP - removed lecturer from public registration
ROLE_MAP = {
    "student": 1,
    "supervisor": 2,
    "admin": 4,
}

# Public roles available for registration
PUBLIC_ROLES = {
    "student": 1,
    "supervisor": 2,
}

def user_register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Show success message and redirect to login page
            messages.success(request, "Registration successful! Please login with your credentials.")
            return redirect('accounts:login')
            
        else:
            # Display form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = UserRegistrationForm()
    
    # Only show public roles in template context
    return render(request, 'accounts/register.html', {
        'form': form,
        'public_roles': PUBLIC_ROLES
    })

def user_login(request):
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        selected_role = request.POST.get("role")

        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)

            if user is not None:
                # Handle role-based redirection
                if selected_role:
                    expected_type = ROLE_MAP.get(selected_role)
                    if expected_type and user.user_type != expected_type:
                        messages.error(request, "Role mismatch! Please select the correct role for your account.")
                        return redirect('accounts:login')
                
                # Login success
                user.backend = 'accounts.backend.IDBackend'
                login(request, user)
                messages.success(request, f"Welcome, {user.first_name}!")

                # Redirect based on user type
                if user.user_type == 1:  # Student
                    return redirect('attachments:student_dashboard')
                elif user.user_type == 2:  # Supervisor
                    return redirect('evaluations:supervisor_dashboard')
                elif user.user_type == 3:  # Lecturer (created by admin)
                    return redirect('evaluations:lecturer_dashboard')
                elif user.user_type == 4:  # Admin
                    return redirect('attachments:admin_dashboard')  # Redirect to our custom admin dashboard
                else:
                    # Fallback for unknown user types
                    return redirect('attachments:dashboard')
                    
            else:
                messages.error(request, "Invalid ID or password.")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = UserLoginForm()

    return render(request, 'accounts/login.html', {
        'form': form,
        'role_map': ROLE_MAP  # Pass all roles for login (including lecturers)
    })

#admin views page for login and takes to the portal

def admin_login(request):
    """
    Dedicated admin login page
    """
    if request.user.is_authenticated and (request.user.is_superuser or request.user.user_type == 4):
        return redirect('attachments:admin_dashboard')
    
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)

            if user is not None:
                # Check if user is admin or superuser
                if not (user.is_superuser or user.user_type == 4):
                    messages.error(request, "Access denied. Admin privileges required.")
                    return redirect('accounts:admin_login')
                
                # Login success
                user.backend = 'accounts.backend.IDBackend'
                login(request, user)
                messages.success(request, f"Welcome to Admin Portal, {user.first_name}!")
                
                # Redirect to admin dashboard
                return redirect('attachments:admin_dashboard')
            else:
                messages.error(request, "Invalid email or password.")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = UserLoginForm()

    return render(request, 'accounts/admin_login.html', {'form': form})

def admin_portal(request):
    """
    Admin portal homepage - shows quick access to all admin features
    """
    if not request.user.is_authenticated or not (request.user.is_superuser or request.user.user_type == 4):
        return redirect('accounts:admin_login')
    
    # Quick stats for the portal
    total_students = User.objects.filter(user_type=1).count()
    total_lecturers = Lecturer.objects.filter(is_active=True).count()
    total_placements = PlacementFormSubmission.objects.count()
    pending_placements = PlacementFormSubmission.objects.filter(status='pending').count()
    
    context = {
        'total_students': total_students,
        'total_lecturers': total_lecturers,
        'total_placements': total_placements,
        'pending_placements': pending_placements,
    }
    
    return render(request, 'accounts/admin_portal.html', context)




@login_required
def user_logout(request):
    logout(request)
    messages.info(request, "Logged out successfully.")
    return redirect('accounts:login')

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

def check_username(request):
    username = request.GET.get('username')
    exists = User.objects.filter(student_id__iexact=username).exists() or User.objects.filter(staff_id__iexact=username).exists()
    return JsonResponse({'is_taken': exists})

def about(request):
    return render(request, 'about.html')

@login_required
def upload_profile_picture(request):
    if request.method == "POST" and request.FILES.get("profile_picture"):
        request.user.profile_picture = request.FILES["profile_picture"]
        request.user.save()
        messages.success(request, "Profile picture updated successfully.")
    return redirect("accounts:profile")

def check_username(request):
    student_id = request.GET.get('student_id', None)
    is_taken = User.objects.filter(student_id__iexact=student_id).exists()
    return JsonResponse({'is_taken': is_taken})
    
@login_required
def student_dashboard(request):
    return render(request, 'attachments/dashboard.html', {'user': request.user})

@login_required  
def supervisor_dashboard(request):
    return render(request, 'evaluations/supervisor_dashboard.html', {'user': request.user})

@login_required
def lecturer_dashboard(request):
    return render(request, 'evaluations/lecturer_dashboard.html', {'user': request.user})

def about(request):
    """
    Renders the About Us page.
    """
    return render(request, 'about.html')