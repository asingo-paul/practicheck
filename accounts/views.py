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


# accounts/views.py
# def user_login(request):
#     if request.method == 'POST':
#         form = UserLoginForm(data=request.POST)
#         if form.is_valid():
#             user = form.get_user()
#             login(request, user)
            
#             print(f"DEBUG: User {user.username} logged in with type {user.user_type}")
#             print(f"DEBUG: User authenticated: {user.is_authenticated}")

#             # Redirect based on user type
#             if user.user_type == 1:  # Student
#                 # Check if student has any attachments
#                 attachments = Attachment.objects.filter(student=user)
#                 if attachments.exists():
#                     return redirect('attachments:dashboard')
#                 else:
#                     return redirect('attachments:welcome')
                    
#             elif user.user_type == 2:  # Supervisor
#                 return redirect('evaluations:supervisor_dashboard')
                
#             elif user.user_type == 3:  # Lecturer
#                 return redirect('evaluations:lecturer_dashboard')
                
#             elif user.user_type == 4:  # Admin
#                 return redirect('/admin/')
            
#             # fallback
#             return redirect('home')
#     else:
#         form = UserLoginForm()
    
#     return render(request, 'accounts/login.html', {'form': form})



# def user_login(request):
#     if request.method == 'POST':
#         form = UserLoginForm(data=request.POST)
#         if form.is_valid():
#             user = form.get_user()
#             login(request, user)
            
#             print(f"DEBUG: User {user.username} logged in with type {user.user_type}")
#             print(f"DEBUG: User authenticated: {user.is_authenticated}")


#     if request.method == 'POST':
#         form = UserLoginForm(data=request.POST)
#         if form.is_valid():
#             user = form.get_user()
#             login(request, user)
            
#             # Redirect based on user type
#             if user.user_type == 1:  # Student
#                 # Check if student has any attachments
#                 attachments = Attachment.objects.filter(student=user)
#                 if attachments.exists():
#                     return redirect('attachments:dashboard')
#                 else:
#                     # If no attachment yet, show a welcome page
#                     return redirect('attachments:welcome')
                    
#             elif user.user_type == 2:  # Supervisor
#                 return redirect('evaluations:supervisor_dashboard')
                
#             elif user.user_type == 3:  # Lecturer
#                 return redirect('evaluations:lecturer_dashboard')
                
#             elif user.user_type == 4:  # Admin
#                 return redirect('/admin/')
                
#     else:
#         form = UserLoginForm()
#     return render(request, 'accounts/login.html', {'form': form})


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
    
    if hasattr(user, 'student_profile'):
        profile = user.student_profile
    elif hasattr(user, 'supervisor_profile'):
        profile = user.supervisor_profile
    elif hasattr(user, 'lecturer_profile'):
        profile = user.lecturer_profile
    
    return render(request, 'accounts/profile.html', {'user': user, 'profile': profile})