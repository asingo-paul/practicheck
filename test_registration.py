import os
import django
from django.test import TestCase
from attachments.forms import AttachmentForm
from django.utils import timezone
from datetime import timedelta

# Setup Django environment

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'practicheck.settings')
django.setup()

from accounts.forms import UserRegistrationForm


class RegistrationAndAttachmentTests(TestCase):
    def test_registration_and_attachment_submission(self):
        print("\n--- Testing Registration and Attachment Form ---")

        # Step 1: Register a new student user
        registration_data = {
            'username': 'test_student_new',
            'email': 'test_student_new@example.com',
            'first_name': 'Test',
            'last_name': 'StudentNew',
            'user_type': '1',  # Student
            'password1': 'testpass123',
            'password2': 'testpass123',
        }

        reg_form = UserRegistrationForm(registration_data)
        print(f"Registration form valid: {reg_form.is_valid()}")
        self.assertTrue(reg_form.is_valid(), msg=f"Registration form errors: {reg_form.errors}")

        user = reg_form.save(commit=True)
        print(f"✅ User created: {user.username} (type: {user.user_type})")

        # Step 2: Create an attachment for that student
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

        attach_form = AttachmentForm(attachment_data)
        print(f"Attachment form valid: {attach_form.is_valid()}")
        self.assertTrue(attach_form.is_valid(), msg=f"Attachment form errors: {attach_form.errors}")

        if attach_form.is_valid():
            attachment = attach_form.save(commit=False)
            attachment.student = user  # ✅ correct field for your model
            attachment.save()
            print(f"✅ Attachment saved for: {attachment.student.username} at {attachment.organization}")
