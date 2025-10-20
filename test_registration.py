# test_registration.py
from django.test import TestCase
from accounts.forms import UserRegistrationForm
from students.forms import StudentProfileForm


class RegistrationFormTests(TestCase):
    def test_student_registration_and_profile_creation(self):
        # Simulate registration form submission
        form_data = {
            'username': 'test_student_new',
            'email': 'test_student_new@example.com',
            'first_name': 'Test',
            'last_name': 'StudentNew',
            'user_type': '1',  # Student
            'password1': 'testpass123',
            'password2': 'testpass123',
        }

        form = UserRegistrationForm(form_data)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

        user = form.save(commit=False)
        user.save()  # Save user so it exists in DB

        # Now test StudentProfileForm
        profile_data = {
            'student_id': 'ST9999',
            'course': 'Test Course',
            'year_of_study': 3,
            'university': 'Test University',
            'department': 'Test Department'
        }

        profile_form = StudentProfileForm(profile_data)
        self.assertTrue(profile_form.is_valid(), f"Profile errors: {profile_form.errors}")

        profile = profile_form.save(commit=False)
        profile.user = user
        profile.save()

        # Verify profile created
        self.assertEqual(profile.user.username, 'test_student_new')
        print("✅ Student profile created successfully.")
