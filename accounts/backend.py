from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from .models import StudentProfile, LecturerProfile
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import StudentProfile
from .models import StudentProfile, LecturerProfile
# from attachments.models import LecturerProfile, SupervisorProfile
from attachments.models import Lecturer

User = get_user_model()


class IDBackend(ModelBackend):
    """
    Authenticate using student_id, staff_id, or email.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        user = None
        
        # Try student ID
        try:
            student_profile = StudentProfile.objects.get(student_id=username)
            user = student_profile.user
        except StudentProfile.DoesNotExist:
            pass
        
        # Try lecturer staff ID
        if not user:
            try:
                lecturer = Lecturer.objects.get(staff_id=username)
                user = lecturer.user
            except Lecturer.DoesNotExist:
                pass
        
        # Try email as fallback
        if not user:
            try:
                user = User.objects.get(email=username)
            except User.DoesNotExist:
                return None
        
        # Check password and user status
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        
        return None




class RoleBasedAuthBackend(ModelBackend):
    """
    Custom authentication backend that handles different login methods per role:
    - Students: Student ID + Password
    - Lecturers: Staff ID + Password  
    - Supervisors: Email + Password
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Get the selected role from request or kwargs
            role = None
            if request and hasattr(request, 'POST'):
                role = request.POST.get('role', 'student')
            role = role or kwargs.get('role', 'student')
            
            if role == 'student':
                # Student login: Find by Student ID in StudentProfile
                student_profile = StudentProfile.objects.select_related('user').filter(
                    student_id__iexact=username
                ).first()
                
                if student_profile and student_profile.user.check_password(password):
                    return student_profile.user
            
            elif role == 'lecturer':
                # Lecturer login: Find by Staff ID in LecturerProfile
                lecturer_profile = LecturerProfile.objects.select_related('user').filter(
                    staff_id__iexact=username
                ).first()
                
                if lecturer_profile and lecturer_profile.user.check_password(password):
                    return lecturer_profile.user
            
            elif role == 'supervisor':
                # Supervisor login: Find by Email in User model
                user = User.objects.filter(
                    email__iexact=username, 
                    user_type=2  # Supervisor type
                ).first()
                
                if user and user.check_password(password):
                    return user
            
            # Fallback: Try default email authentication for admins and others
            user = User.objects.filter(email__iexact=username).first()
            if user and user.check_password(password):
                return user
                
        except Exception as e:
            print(f"Authentication error: {e}")
            return None
        
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None