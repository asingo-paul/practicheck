
# attachments/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings

User = get_user_model()

class Industry(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    
    def __str__(self):
        return self.name

class Attachment(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attachments')
    industry = models.ForeignKey(Industry, on_delete=models.SET_NULL, null=True, blank=True)
    organization = models.CharField(max_length=200)
    department = models.CharField(max_length=100, blank=True)
    supervisor_name = models.CharField(max_length=100)
    supervisor_email = models.EmailField(blank=True)  # Make it optional temporarily
    supervisor_phone = models.CharField(max_length=15, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=(
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ), default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.organization}"
    
    @property
    def is_active(self):
        return self.status in ['approved', 'ongoing']

    @property
    def days_completed(self):
        """Number of days completed in the attachment"""
        if self.status in ['approved', 'ongoing']:
            completed = (timezone.now().date() - self.start_date).days
            return max(0, min(completed, (self.end_date - self.start_date).days))
        return 0

    @property
    def total_days(self):
        """Total number of days in the attachment"""
        return (self.end_date - self.start_date).days

    @property
    def progress_percentage(self):
        """Progress percentage (0-100)"""
        if self.total_days > 0:
            return min(100, max(0, int((self.days_completed / self.total_days) * 100)))
        return 0
    
    @property
    def days_remaining(self):
        from django.utils import timezone
        if self.end_date and self.status in ['approved', 'ongoing']:
            remaining = (self.end_date - timezone.now().date()).days
            return max(0, remaining)
        return 0


    class Meta:
         # this prevent multiple attachments per student at the database level
        constraints = [
            models.UniqueConstraint(fields=['student'], name='unique_student_attachment')
        ]

class LogbookEntry(models.Model):
    attachment = models.ForeignKey(Attachment, on_delete=models.CASCADE, related_name='logbook_entries')
    entry_date = models.DateField()
    department_section = models.CharField(max_length=100, help_text="Department or section where you worked today")
    tasks = models.TextField(help_text="Tasks you worked on today")
    skills_learned = models.TextField(help_text="New skills or knowledge gained")
    achievements = models.TextField(blank=True, help_text="Notable achievements or accomplishments")
    challenges = models.TextField(blank=True, help_text="Challenges faced and how you addressed them")
    hours_worked = models.DecimalField(max_digits=4, decimal_places=1, validators=[MinValueValidator(0.5), MaxValueValidator(24)])
    supervisor_comments = models.TextField(blank=True)
    edit_count = models.IntegerField(default=0, validators=[MaxValueValidator(2)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-entry_date']
        unique_together = ['attachment', 'entry_date']
    
    def __str__(self):
        return f"Logbook Entry - {self.attachment.student.username} - {self.entry_date}"
    
    def can_edit(self):
        return self.edit_count < 2


@receiver(post_save, sender=LogbookEntry)
def send_supervisor_notification(sender, instance, created, **kwargs):
    """Send email notification to supervisor when a new entry is created"""
    if created and instance.attachment.supervisor_email:
        subject = f'New Logbook Entry - {instance.attachment.student.get_full_name()}'
        message = f'''
        {instance.attachment.student.get_full_name()} has submitted a new logbook entry.
        
        Date: {instance.entry_date}
        Organization: {instance.attachment.organization}
        Department: {instance.department_section}
        Hours Worked: {instance.hours_worked}
        
        Tasks: {instance.tasks[:100]}...
        
        Please review the entry in the supervisor portal.
        '''
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [instance.attachment.supervisor_email],
            fail_silently=True,
        )