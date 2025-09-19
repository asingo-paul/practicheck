from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from .models import StudentProfile, LecturerProfile

User = get_user_model()

class IDBackend(ModelBackend):
    """
    Authenticate using student_id or staff_id from profile models.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Try to find a student with this ID
            student_profile = StudentProfile.objects.get(student_id=username)
            user = student_profile.user
        except StudentProfile.DoesNotExist:
            try:
                # Try to find a lecturer with this ID
                lecturer_profile = LecturerProfile.objects.get(staff_id=username)
                user = lecturer_profile.user
            except LecturerProfile.DoesNotExist:
                # Fall back to email authentication for supervisors
                try:
                    user = User.objects.get(email=username)
                except User.DoesNotExist:
                    return None
        
        if user.check_password(password):
            return user
        return None