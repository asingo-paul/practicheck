import os
import django
from django.test import TestCase
from attachments.forms import AttachmentForm  # ✅ Use the correct form

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'practicheck.settings')
django.setup()

from accounts.forms import UserRegistrationForm
from django.utils import timezone
from datetime import timedelta


class RegistrationTest(TestCase):
    def test_registration(self):
        print("Testing registration form...")

        # Step 1: Test user registration
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
        print(f"Form is valid: {form.is_valid()}")

        self.assertTrue(form.is_valid(), msg=f"Form errors: {form.errors}")

        user = form.save(commit=False)
        print(f"User created (not saved yet): {user.username}, type: {user.user_type}")

        # Step 2: Test Attachment form for this user
        start_date = timezone.now().date() + timedelta(days=5)
        end_date = start_date + timedelta(days=60)

        attachment_data = {
            'organization': 'Test Company',
            'department': 'IT Department',
            'supervisor_name': 'John Doe',
            'supervisor_email': 'john@example.com',
            'supervisor_phone': '0712345678',
            'start_date': start_date,
            'end_date': end_date,
        }

        attachment_form = AttachmentForm(attachment_data)
        print(f"Attachment form valid: {attachment_form.is_valid()}")
        self.assertTrue(attachment_form.is_valid(), msg=f"Attachment form errors: {attachment_form.errors}")

        if attachment_form.is_valid():
            attachment = attachment_form.save(commit=False)
            attachment.user = user  # assuming your Attachment model has a 'user' ForeignKey
            print("Attachment form validated and ready to save.")
        else:
            print("Attachment form errors:", attachment_form.errors)
