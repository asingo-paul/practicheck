from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings

class CustomUser(AbstractUser):
    username = None  # Remove default username

    USER_TYPE_CHOICES = (
        (1, "Student"),
        (2, "Supervisor"),
        (3, "Lecturer"),
        (4, "Admin"),
    )
    user_type = models.PositiveSmallIntegerField(choices=USER_TYPE_CHOICES, default=1)

    email = models.EmailField(unique=True, null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    # FIXED: Remove duplicate __str__ method, keep only this one:
    def __str__(self):
        if self.user_type == 1 and hasattr(self, 'student_profile'):
            return self.student_profile.student_id
        elif self.user_type == 3 and hasattr(self, 'lecturer_profile'):
            return self.lecturer_profile.staff_id
        elif self.user_type == 2 and hasattr(self, 'supervisor_profile'):
            return f"{self.get_full_name()} - {self.supervisor_profile.organization}"
        return self.email or f"User {self.id}"
    # def __str__(self):
    #     return self.student_id or self.staff_id or self.email or self.username


class StudentProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_profile')
    student_id = models.CharField(max_length=20, unique=True)
    course = models.CharField(max_length=100)
    year_of_study = models.PositiveSmallIntegerField()
    university = models.CharField(max_length=200)
    department = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.student_id}"


class SupervisorProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='supervisor_profile')
    organization = models.CharField(max_length=200)
    position = models.CharField(max_length=100)
    email = models.EmailField(null=True, blank=True)
    department = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.organization}"


class LecturerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='lecturer_profile')
    staff_id = models.CharField(max_length=20, unique=True)
    department = models.CharField(max_length=100)
    faculty = models.CharField(max_length=100)
    email = models.EmailField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.staff_id}"
