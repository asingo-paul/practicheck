# check_users.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'practicheck.settings')
django.setup()

from accounts.models import User, StudentProfile, SupervisorProfile, LecturerProfile

print("=== CURRENT USERS IN DATABASE ===")
users = User.objects.all().order_by('date_joined')
for user in users:
    profile_type = "None"
    if hasattr(user, 'student_profile'):
        profile_type = "Student"
    elif hasattr(user, 'supervisor_profile'):
        profile_type = "Supervisor"
    elif hasattr(user, 'lecturer_profile'):
        profile_type = "Lecturer"
    
    print(f"ID: {user.id}, Username: {user.username}, Email: {user.email}, Type: {user.user_type} ({user.get_user_type_display()}), Profile: {profile_type}, Joined: {user.date_joined}")

print("\n=== USER TYPE COUNTS ===")
for i in range(1, 5):
    count = User.objects.filter(user_type=i).count()
    print(f"Type {i} ({User.USER_TYPE_CHOICES[i-1][1]}): {count} users")

print("\n=== PROFILES ===")
print(f"Student profiles: {StudentProfile.objects.count()}")
print(f"Supervisor profiles: {SupervisorProfile.objects.count()}")
print(f"Lecturer profiles: {LecturerProfile.objects.count()}")