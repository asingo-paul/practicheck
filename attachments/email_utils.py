from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)

def send_lecturer_credentials(email, first_name, staff_id, password):
    """Send login credentials to lecturer via email with HTML template"""
    
    context = {
        'first_name': first_name,
        'staff_id': staff_id,
        'password': password,
        'login_url': f"{settings.SITE_URL}/accounts/login/",
        'support_email': getattr(settings, 'SUPPORT_EMAIL', 'practicheck@gmail.com'),
    }
    
    try:
        # Render HTML email
        html_message = render_to_string('attachments/emails/lecturer_credentials.html', context)
        plain_message = strip_tags(html_message)
        
        subject = 'Your PractiCheck Lecturer Account Credentials'
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Lecturer credentials email sent successfully to {email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send lecturer credentials email to {email}: {str(e)}")
        return False

def send_lecturer_password_reset(email, first_name, staff_id, new_password):
    """Send password reset notification to lecturer"""
    
    context = {
        'first_name': first_name,
        'staff_id': staff_id,
        'password': new_password,
        'login_url': f"{settings.SITE_URL}/accounts/login/",
        'support_email': getattr(settings, 'SUPPORT_EMAIL', 'practicheck@gmail.com'),
    }
    
    try:
        html_message = render_to_string('attachments/emails/password_reset.html', context)
        plain_message = strip_tags(html_message)
        
        subject = 'PractiCheck - Password Reset'
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Password reset email sent successfully to {email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send password reset email to {email}: {str(e)}")
        return False