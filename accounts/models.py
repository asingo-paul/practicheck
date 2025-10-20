from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.conf import settings

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        """
        Create and return a regular user with the given email and password.
        """
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and return a superuser with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('user_type', 4)  # Admin type

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

# class CustomUser(AbstractUser):
#     username = None  # Remove default username

#     USER_TYPE_CHOICES = (
#         (1, "Student"),
#         (2, "Supervisor"),
#         (3, "Lecturer"),
#         (4, "Admin"),
#     )
#     user_type = models.PositiveSmallIntegerField(choices=USER_TYPE_CHOICES, default=1)

#     email = models.EmailField(unique=True)
#     student_id = models.CharField(max_length=20, unique=True, blank=True, null=True)

#     USERNAME_FIELD = 'email'
#     REQUIRED_FIELDS = []  # Remove 'username' from required fields

#     objects = CustomUserManager()  # Add this line

#     def __str__(self):
#         if self.user_type == 1 and hasattr(self, 'student_profile'):
#             return self.student_profile.student_id
#         elif self.user_type == 3 and hasattr(self, 'lecturer_profile'):
#             return self.lecturer_profile.staff_id
#         elif self.user_type == 2 and hasattr(self, 'supervisor_profile'):
#             return f"{self.get_full_name()} - {self.supervisor_profile.organization}"
#         return self.email or f"User {self.id}"


class CustomUser(AbstractUser):
    username = None  # Remove default username

    USER_TYPE_CHOICES = (
        (1, "Student"),
        (2, "Supervisor"),
        (3, "Lecturer"),
        (4, "Admin"),
    )
    user_type = models.PositiveSmallIntegerField(choices=USER_TYPE_CHOICES, default=1)

    email = models.EmailField(unique=True)
    
    # Student-specific fields
    student_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    year_of_study = models.PositiveSmallIntegerField(blank=True, null=True)
    university = models.CharField(max_length=200, blank=True, null=True)
    
    # Supervisor-specific fields
    organization = models.CharField(max_length=200, blank=True, null=True)
    position = models.CharField(max_length=100, blank=True, null=True)
    supervisor_department = models.CharField(max_length=100, blank=True, null=True)

    # Department and Course as ForeignKey (add these)
    department = models.ForeignKey('attachments.Department', on_delete=models.SET_NULL, null=True, blank=True)
    course = models.ForeignKey('attachments.Course', on_delete=models.SET_NULL, null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # Remove 'username' from required fields

    objects = CustomUserManager()

    def __str__(self):
        if self.user_type == 1 and self.student_id:
            return self.student_id
        elif self.user_type == 3 and hasattr(self, 'lecturer_profile'):
            return self.lecturer_profile.staff_id
        elif self.user_type == 2 and self.organization:
            return f"{self.get_full_name()} - {self.organization}"
        return self.email or f"User {self.id}"

class StudentProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_profile')
    student_id = models.CharField(max_length=20, unique=True)
    course = models.CharField(max_length=100)
    year_of_study = models.PositiveSmallIntegerField(null=True, blank=True)  # Allow null
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
    phone_number = models.CharField(max_length=15, blank=True)

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