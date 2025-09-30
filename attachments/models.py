# attachments/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User

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
    report = models.FileField(upload_to="reports/", blank=True, null=True)
    status = models.CharField(max_length=20, choices=(
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ), default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # this prevent multiple attachments per student at the database level
        constraints = [
            models.UniqueConstraint(fields=['student'], name='unique_student_attachment')
        ]
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.organization}"
    
    @property
    def is_active(self):
        """Check if attachment is currently active"""
        if not self.start_date or not self.end_date:
            return False
        
        today = timezone.now().date()
        return self.start_date <= today <= self.end_date and self.status in ['approved', 'ongoing']

    @property
    def days_completed(self):
        """Calculate days completed based on actual dates"""
        if not self.start_date or not self.end_date:
            return 0
            
        today = timezone.now().date()
            
        if today < self.start_date:
            # Attachment hasn't started yet
            return 0
        elif today > self.end_date:
            # Attachment has ended
            return (self.end_date - self.start_date).days
        else:
            # Attachment is ongoing
            return (today - self.start_date).days

    @property
    def total_days(self):
        """Total number of days in the attachment"""
        if not self.start_date or not self.end_date:
            return 0
        return (self.end_date - self.start_date).days

    @property
    def progress_percentage(self):
        """Calculate progress percentage based on actual dates"""
        if not self.start_date or not self.end_date:
            return 0
        
        total_days = self.total_days
        if total_days <= 0:
            return 100 if self.status == 'completed' else 0
        
        days_completed = self.days_completed
        progress = min(100, max(0, (days_completed / total_days) * 100))
        return round(progress)
    
    @property
    def days_remaining(self):
        """Calculate days remaining based on actual dates"""
        if not self.start_date or not self.end_date:
            return 0
        
        today = timezone.now().date()
        
        if today < self.start_date:
            # Attachment hasn't started yet
            return (self.end_date - self.start_date).days
        elif today > self.end_date:
            # Attachment has ended
            return 0
        else:
            # Attachment is ongoing
            return (self.end_date - today).days

   

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


class Department(models.Model):
    name = models.CharField(max_length=200)
    #code = models.CharField(max_length=10, unique=True)
    code = models.CharField(max_length=10, unique=True, blank=True, null=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name


class PlacementFormSubmission(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='student_placement_forms')
    
    # Student Details
    registration_number = models.CharField(max_length=20)
    phone_number = models.CharField(max_length=15)
    
    # Course Details
    course_name = models.CharField(max_length=200)
    year_of_study = models.CharField(max_length=10, choices=[
        ('Year 1', 'Year 1'),
        ('Year 2', 'Year 2'),
        ('Year 3', 'Year 3'),
        ('Year 4', 'Year 4'),
        ('Year 5', 'Year 5'),
    ])
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='placement_forms')
    
    # Firm Details
    firm_name = models.CharField(max_length=200)
    firm_email = models.EmailField()
    town_city = models.CharField(max_length=100)
    land_mark = models.CharField(max_length=200)
    
    # Supervisor Details
    supervisor_name = models.CharField(max_length=100)
    supervisor_phone = models.CharField(max_length=15)
    supervisor_email = models.EmailField()
    
    # Period of Attachment
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Off Days (store as JSON)
    off_days = models.JSONField(default=list)
    
    # Status
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['student', 'start_date']
    
    def __str__(self):
        return f"Placement Form - {self.student.get_full_name()} - {self.start_date}"
    
    @property
    def is_assigned(self):
        return hasattr(self, 'student_assignment')


@receiver(post_save, sender=LogbookEntry)
def send_supervisor_notification(sender, instance, created, **kwargs):
    if created and instance.attachment.supervisor_email:
        subject = f'New Logbook Entry - {instance.attachment.student.get_full_name()}'
        message = f"{instance.attachment.student.get_full_name()} submitted a logbook entry on {instance.entry_date}."
        send_mail(
            subject, message,
            settings.DEFAULT_FROM_EMAIL,
            [instance.attachment.supervisor_email],
            fail_silently=True,
        )

class ReportUpload(models.Model):
    attachment = models.ForeignKey("Attachment", on_delete=models.CASCADE, related_name="reports")
    file = models.FileField(upload_to="reports/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.attachment.organization} - {self.file.name}"
    

class Report(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    document = models.FileField(upload_to='reports/')
    submission_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    feedback = models.TextField(blank=True, null=True)
    version = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.title} (v{self.version}) - {self.student}"
    

class Message(models.Model):
    sender = models.ForeignKey(User, related_name="sent_messages", on_delete=models.CASCADE)
    recipient = models.ForeignKey(User, related_name="received_messages", on_delete=models.CASCADE)
    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField()
    attachment = models.FileField(upload_to="messages/", blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

class Announcement(models.Model):
    title = models.CharField(max_length=255)
    body = models.TextField()
    posted_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)




class Lecturer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='attachment_lecturer')
    staff_id = models.CharField(max_length=20, unique=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='attachment_lecturers')
    phone_number = models.CharField(max_length=15, blank=True)
    office_location = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    max_students = models.IntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.department.name}"

class StudentAssignment(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='student_assignments')
    lecturer = models.ForeignKey(Lecturer, on_delete=models.CASCADE, related_name='assigned_students')
    placement_form = models.ForeignKey('PlacementFormSubmission', on_delete=models.CASCADE)
    assigned_date = models.DateTimeField(auto_now_add=True)
    academic_year = models.CharField(max_length=9)  # e.g., "2024-2025"
    
    class Meta:
        unique_together = ['student', 'academic_year']
    
    def __str__(self):
        return f"{self.student.get_full_name()} -> {self.lecturer.user.get_full_name()}"