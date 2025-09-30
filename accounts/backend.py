from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import StudentProfile
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