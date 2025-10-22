# test_registration.py
import os
import django
from django.test import TestCase
from students.forms import StudentProfileForm 

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'practicheck.settings')
django.setup()

from accounts.forms import UserRegistrationForm

# Test the registration form
form_data = {
    'username': 'test_student_new',
    'email': 'test_student_new@example.com',
    'first_name': 'Test',
    'last_name': 'StudentNew',
    'user_type': '1',  # Student
    'password1': 'testpass123',
    'password2': 'testpass123',
}

print("Testing registration form...")
form = UserRegistrationForm(form_data)
print(f"Form is valid: {form.is_valid()}")

if form.is_valid():
    print("Form is valid, testing save...")
    user = form.save(commit=False)
    print(f"User created (not saved yet): {user.username}, type: {user.user_type}")
    
    # Now test profile creation
    if user.user_type == 1:  # Student
        profile_data = {
            'student_id': 'ST9999',
            'course': 'Test Course',
            'year_of_study': 3,
            'university': 'Test University',
            'department': 'Test Department'
        }
        profile_form = StudentProfileForm(profile_data)
        print(f"Student profile form valid: {profile_form.is_valid()}")
        if profile_form.is_valid():
            profile = profile_form.save(commit=False)
            profile.user = user
            profile.save()
            print("Student profile created successfully!")
        else:
            print("Student profile errors:", profile_form.errors)
else:
    print("Form errors:", form.errors)