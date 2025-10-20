from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

# Set up logger
logger = logging.getLogger(__name__)

def send_welcome_email(user, user_type):
    """
    Send welcome email to newly registered users
    """
    try:
        if user_type == 1:  # Student
            subject = 'Welcome to PractiCheck - Student Account Created'
            template = 'accounts/emails/welcome_student.html'
            context = {
                'first_name': user.first_name,
                'student_id': user.student_id,
                'university': user.university,
                'department': user.department.name if user.department else 'Not specified',
                'course': user.course.name if user.course else 'Not specified',
                'year_of_study': user.year_of_study,
                'site_url': getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'practicheck@gmail.com'),
            }
        elif user_type == 2:  # Supervisor
            subject = 'Welcome to PractiCheck - Supervisor Account Created'
            template = 'accounts/emails/welcome_supervisor.html'
            context = {
                'first_name': user.first_name,
                'organization': user.organization,
                'position': user.position,
                'department': user.supervisor_department or 'Not specified',
                'site_url': getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000'),
                'support_email': getattr(settings, 'SUPPORT_EMAIL', 'practicheck@gmail.com'),
            }
        else:
            logger.warning(f"Invalid user type for welcome email: {user_type}")
            return False
        
        # Check if email backend is configured
        if not hasattr(settings, 'EMAIL_BACKEND'):
            logger.info("Email backend not configured. Skipping email sending.")
            return False
        
        # Render HTML email template
        html_message = render_to_string(template, context)
        plain_message = strip_tags(html_message)
        
        # Send email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=True,  # Don't raise errors if email fails
        )
        
        logger.info(f"Welcome email sent successfully to {user.email} (User Type: {user_type})")
        return True
        
    except Exception as e:
        logger.error(f"Error sending welcome email to {user.email}: {str(e)}")
        return False

def send_admin_notification_email(user, user_type):
    """
    Send notification to admin when new user registers
    """
    try:
        # Get admin emails from settings or use default
        admin_emails = getattr(settings, 'ADMIN_EMAILS', ['practicheck@gmail.com'])
        
        if not admin_emails:
            logger.warning("No admin emails configured for notifications")
            return False
        
        if user_type == 1:  # Student
            subject = '🎓 New Student Registration - PractiCheck'
            user_type_name = 'Student'
            details = f"""
📚 Student Details:
• Student ID: {user.student_id}
• University: {user.university}
• Department: {user.department.name if user.department else 'Not specified'}
• Course: {user.course.name if user.course else 'Not specified'}
• Year of Study: {user.year_of_study}
            """
        elif user_type == 2:  # Supervisor
            subject = '👔 New Supervisor Registration - PractiCheck'
            user_type_name = 'Supervisor'
            details = f"""
🏢 Organization Details:
• Organization: {user.organization}
• Position: {user.position}
• Department: {user.supervisor_department or 'Not specified'}
            """
        else:
            logger.warning(f"Invalid user type for admin notification: {user_type}")
            return False
        
        message = f"""
🔔 New {user_type_name} Registration

👤 User Information:
• Name: {user.get_full_name()}
• Email: {user.email}
• User Type: {user_type_name}

{details}

📅 Registration Date: {user.date_joined.strftime('%Y-%m-%d at %H:%M')}
🌐 Registered via: Public Registration Portal

---
This is an automated notification from PractiCheck System.
        """
        
        # Check if email backend is configured
        if not hasattr(settings, 'EMAIL_BACKEND'):
            logger.info("Email backend not configured. Skipping admin notification.")
            return False
        
        # Send email
        send_mail(
            subject=subject,
            message=message.strip(),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=admin_emails,
            fail_silently=True,  # Don't raise errors for admin notifications
        )
        
        logger.info(f"Admin notification sent for new {user_type_name.lower()} registration: {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending admin notification email: {str(e)}")
        return False

def send_bulk_welcome_emails(users):
    """
    Send welcome emails to multiple users (for batch processing)
    """
    success_count = 0
    failure_count = 0
    
    for user in users:
        if send_welcome_email(user, user.user_type):
            success_count += 1
        else:
            failure_count += 1
    
    logger.info(f"Bulk email sending completed: {success_count} successful, {failure_count} failed")
    return success_count, failure_count

def test_email_configuration():
    """
    Test function to verify email configuration is working
    """
    try:
        send_mail(
            subject='PractiCheck - Email Configuration Test',
            message='This is a test email to verify your email configuration is working correctly.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.ADMIN_EMAILS[0] if hasattr(settings, 'ADMIN_EMAILS') and settings.ADMIN_EMAILS else 'practicheck@gmail.com'],
            fail_silently=False,
        )
        logger.info("Email configuration test: SUCCESS")
        return True
    except Exception as e:
        logger.error(f"Email configuration test: FAILED - {str(e)}")
        return False