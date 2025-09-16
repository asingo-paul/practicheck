from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        (1, 'Student'),
        (2, 'Supervisor'),
        (3, 'Lecturer'),
        (4, 'Admin'),
    )
    
    user_type = models.PositiveSmallIntegerField(choices=USER_TYPE_CHOICES, default=1)
    phone_number = models.CharField(max_length=15, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.username} - {self.get_user_type_display()}"

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    student_id = models.CharField(max_length=20, unique=True)
    course = models.CharField(max_length=100)
    year_of_study = models.IntegerField()
    university = models.CharField(max_length=200)
    department = models.CharField(max_length=100)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.student_id}"

class SupervisorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='supervisor_profile')
    organization = models.CharField(max_length=200)
    position = models.CharField(max_length=100)
    department = models.CharField(max_length=100, blank=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.organization}"

class LecturerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='lecturer_profile')
    staff_id = models.CharField(max_length=20, unique=True)
    department = models.CharField(max_length=100)
    faculty = models.CharField(max_length=100)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.staff_id}"

# class CustomUser(AbstractUser):
#     profile_picture = models.ImageField(upload_to="profile_pics/", blank=True, null=True)
