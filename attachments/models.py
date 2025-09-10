from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Attachment(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attachments')
    organization = models.CharField(max_length=200)
    supervisor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='supervised_attachments')
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=(
        ('pending', 'Pending'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ), default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.organization}"

class LogbookEntry(models.Model):
    attachment = models.ForeignKey(Attachment, on_delete=models.CASCADE, related_name='logbook_entries')
    entry_date = models.DateField()
    tasks = models.TextField()
    skills_learned = models.TextField()
    hours_worked = models.DecimalField(max_digits=4, decimal_places=1)
    challenges = models.TextField(blank=True)
    supervisor_comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-entry_date']
    
    def __str__(self):
        return f"Logbook Entry - {self.attachment.student.username} - {self.entry_date}"

class Report(models.Model):
    attachment = models.OneToOneField(Attachment, on_delete=models.CASCADE, related_name='report')
    title = models.CharField(max_length=200)
    document = models.FileField(upload_to='reports/')
    submission_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=(
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ), default='draft')
    feedback = models.TextField(blank=True)
    
    def __str__(self):
        return f"Report - {self.attachment.student.username} - {self.title}"