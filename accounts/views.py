
# accounts/views.py - Updated version
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, authenticate, get_backends
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .forms import UserRegistrationForm, UserLoginForm
from .models import StudentProfile, SupervisorProfile, LecturerProfile
from django.contrib.auth import get_user_model
from attachments.models import Attachment, LogbookEntry, PlacementFormSubmission, Lecturer
from attachments.models import Department, Course
from .email_utils import send_welcome_email, send_admin_notification_email
from django.conf import settings

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
        # Get form data
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        user_type = request.POST.get('user_type')
        
        # Validate required fields
        if not all([first_name, last_name, email, password1, password2, user_type]):
            messages.error(request, "Please fill in all required fields.")
            return render(request, 'accounts/register.html', {
                'departments': Department.objects.filter(university="Machakos University"),
                'public_roles': PUBLIC_ROLES
            })
        
        # Check if passwords match
        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return render(request, 'accounts/register.html', {
                'departments': Department.objects.filter(university="Machakos University"),
                'public_roles': PUBLIC_ROLES
            })
        
        # Check password strength
        if len(password1) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return render(request, 'accounts/register.html', {
                'departments': Department.objects.filter(university="Machakos University"),
                'public_roles': PUBLIC_ROLES
            })
        
        # Check if email already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, "A user with this email already exists.")
            return render(request, 'accounts/register.html', {
                'departments': Department.objects.filter(university="Machakos University"),
                'public_roles': PUBLIC_ROLES
            })
        
        try:
            # Handle student registration
            if user_type == '1':  # Student
                student_id = request.POST.get('student_id')
                year_of_study = request.POST.get('year_of_study')
                department_id = request.POST.get('department')
                course_id = request.POST.get('course')
                
                # Validate student-specific fields
                if not all([student_id, year_of_study, department_id, course_id]):
                    messages.error(request, "Please fill in all student information.")
                    return render(request, 'accounts/register.html', {
                        'departments': Department.objects.filter(university="Machakos University"),
                        'public_roles': PUBLIC_ROLES
                    })
                
                # Check if student ID already exists in BOTH places
                if User.objects.filter(student_id=student_id).exists():
                    messages.error(request, f"A student with ID '{student_id}' already exists. Please use a different Student ID.")
                    return render(request, 'accounts/register.html', {
                        'departments': Department.objects.filter(university="Machakos University"),
                        'public_roles': PUBLIC_ROLES
                    })
                
                if StudentProfile.objects.filter(student_id=student_id).exists():
                    messages.error(request, f"A student with ID '{student_id}' already exists. Please use a different Student ID.")
                    return render(request, 'accounts/register.html', {
                        'departments': Department.objects.filter(university="Machakos University"),
                        'public_roles': PUBLIC_ROLES
                    })
                
                # Validate year of study
                try:
                    year_of_study_int = int(year_of_study)
                    if year_of_study_int < 1 or year_of_study_int > 6:
                        messages.error(request, "Year of study must be between 1 and 6.")
                        return render(request, 'accounts/register.html', {
                            'departments': Department.objects.filter(university="Machakos University"),
                            'public_roles': PUBLIC_ROLES
                        })
                except ValueError:
                    messages.error(request, "Year of study must be a valid number.")
                    return render(request, 'accounts/register.html', {
                        'departments': Department.objects.filter(university="Machakos University"),
                        'public_roles': PUBLIC_ROLES
                    })
                
                try:
                    department = Department.objects.get(id=department_id)
                    course = Course.objects.get(id=course_id)
                except (Department.DoesNotExist, Course.DoesNotExist):
                    messages.error(request, "Invalid department or course selected.")
                    return render(request, 'accounts/register.html', {
                        'departments': Department.objects.filter(university="Machakos University"),
                        'public_roles': PUBLIC_ROLES
                    })
            
            # Create user (moved this AFTER student validation)
            user = User.objects.create_user(
                email=email,
                password=password1,
                first_name=first_name,
                last_name=last_name,
                user_type=int(user_type)
            )
            
            # Initialize email_sent variable
            email_sent = False
            admin_notification_sent = False
            
            # Handle student registration
            if user_type == '1':  # Student
                # Update user with student information
                user.student_id = student_id
                user.year_of_study = year_of_study_int
                user.university = "Machakos University"
                user.department = department
                user.course = course
                user.save()
                
                # Create student profile with the SAME student_id
                try:
                    student_profile = StudentProfile.objects.create(
                        user=user,
                        student_id=student_id,  # Use the same student_id
                        course=course.name,
                        year_of_study=year_of_study_int,
                        university="Machakos University",
                        department=department.name
                    )
                except Exception as e:
                    # If StudentProfile creation fails, delete the user and show error
                    user.delete()
                    if 'UNIQUE' in str(e):
                        messages.error(request, f"Student ID '{student_id}' is already taken. Please use a different Student ID.")
                    else:
                        messages.error(request, f"Error creating student profile: {str(e)}")
                    return render(request, 'accounts/register.html', {
                        'departments': Department.objects.filter(university="Machakos University"),
                        'public_roles': PUBLIC_ROLES
                    })
                
                # Send welcome email to student
                try:
                    email_sent = send_welcome_email(user, 1)
                except Exception as e:
                    print(f"Error sending student welcome email: {e}")
                    email_sent = False
                
                # Send admin notification
                try:
                    admin_notification_sent = send_admin_notification_email(user, 1)
                except Exception as e:
                    print(f"Error sending admin notification: {e}")
                    admin_notification_sent = False
                
            # Handle supervisor registration
            elif user_type == '2':  # Supervisor
                organization = request.POST.get('organization')
                position = request.POST.get('position')
                supervisor_department = request.POST.get('supervisor_department')
                
                if not all([organization, position]):
                    user.delete()
                    messages.error(request, "Please fill in all supervisor information.")
                    return render(request, 'accounts/register.html', {
                        'departments': Department.objects.filter(university="Machakos University"),
                        'public_roles': PUBLIC_ROLES
                    })
                
                user.organization = organization
                user.position = position
                user.supervisor_department = supervisor_department
                user.save()
                
                # Create supervisor profile
                try:
                    supervisor_profile = SupervisorProfile.objects.create(
                        user=user,
                        organization=organization,
                        position=position,
                        department=supervisor_department or '',
                        email=email
                    )
                except Exception as e:
                    user.delete()
                    messages.error(request, f"Error creating supervisor profile: {str(e)}")
                    return render(request, 'accounts/register.html', {
                        'departments': Department.objects.filter(university="Machakos University"),
                        'public_roles': PUBLIC_ROLES
                    })
                
                # Send welcome email to supervisor
                try:
                    email_sent = send_welcome_email(user, 2)
                except Exception as e:
                    print(f"Error sending supervisor welcome email: {e}")
                    email_sent = False
                
                # Send admin notification
                try:
                    admin_notification_sent = send_admin_notification_email(user, 2)
                except Exception as e:
                    print(f"Error sending admin notification: {e}")
                    admin_notification_sent = False
            
            # Show success message with email notification info
            success_message = "Registration successful! Please login with your credentials."
            
            if email_sent:
                success_message += " A welcome email has been sent to your email address."
            else:
                success_message += " Please check your email for login instructions."
            
            messages.success(request, success_message)
            
            return redirect('accounts:login')
            
        except Exception as e:
            # Handle any unexpected errors
            messages.error(request, f"An error occurred during registration: {str(e)}")
            return render(request, 'accounts/register.html', {
                'departments': Department.objects.filter(university="Machakos University"),
                'public_roles': PUBLIC_ROLES
            })
    
    else:
        # GET request - provide departments for the form
        departments = Department.objects.filter(university="Machakos University")
        return render(request, 'accounts/register.html', {
            'departments': departments,
            'public_roles': PUBLIC_ROLES
        })

def user_login(request):
    if request.method == 'POST':
        selected_role = request.POST.get("role", "student")
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if username and password:
            try:
                # Use Django's authenticate function with your custom backend
                user = authenticate(
                    request=request,
                    username=username,
                    password=password
                )
                
                if user is not None:
                    # Verify the role matches the selected role
                    role_matches = False
                    if selected_role == "student" and user.user_type == 1:
                        role_matches = True
                    elif selected_role == "lecturer" and user.user_type == 3:
                        role_matches = True
                    elif selected_role == "supervisor" and user.user_type == 2:
                        role_matches = True
                    elif selected_role == "admin" and user.user_type == 4:
                        role_matches = True
                    
                    if role_matches:
                        # Login success
                        login(request, user)
                        messages.success(request, f"Welcome, {user.first_name}!")

                        # Redirect based on user type
                        if user.user_type == 1:  # Student
                            return redirect('attachments:student_dashboard')
                        elif user.user_type == 2:  # Supervisor
                            return redirect('evaluations:supervisor_dashboard')
                        elif user.user_type == 3:  # Lecturer
                            return redirect('evaluations:lecturer_dashboard')
                        elif user.user_type == 4:  # Admin
                            return redirect('attachments:admin_dashboard')
                        else:
                            return redirect('attachments:dashboard')
                    else:
                        messages.error(request, f"Role mismatch! Please select '{user.get_user_type_display()}' role to login.")
                else:
                    messages.error(request, "Invalid credentials. Please try again.")
                
            except Exception as e:
                messages.error(request, "An error occurred during authentication.")
                print(f"Login error: {e}")
                import traceback
                print(f"Detailed error: {traceback.format_exc()}")
        else:
            messages.error(request, "Please provide both username and password.")
            
        # If we get here, authentication failed
        form = UserLoginForm()
        return render(request, 'accounts/login.html', {
            'form': form,
            'role_map': ROLE_MAP
        })
    
    else:
        # GET request
        form = UserLoginForm()
        return render(request, 'accounts/login.html', {
            'form': form,
            'role_map': ROLE_MAP
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

def check_student_id(request):
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

@login_required
def admin_profile(request):
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

    return render(request, 'accounts/admin_profile.html', {
        'user': user,
        'profile': profile,
        'logbook_entries': logbook_entries,
        'total_entries': total_entries,
        'completion_rate': completion_rate,
    })


def check_student_id(request):
    """Check if student ID is already taken in BOTH User and StudentProfile"""
    student_id = request.GET.get('student_id', '')
    if student_id:
        # Check both User model and StudentProfile model
        is_taken_user = User.objects.filter(student_id__iexact=student_id).exists()
        is_taken_profile = StudentProfile.objects.filter(student_id__iexact=student_id).exists()
        is_taken = is_taken_user or is_taken_profile
        return JsonResponse({'is_taken': is_taken})
    return JsonResponse({'is_taken': False})