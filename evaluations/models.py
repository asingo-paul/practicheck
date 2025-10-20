from django.db import models
from django.contrib.auth import get_user_model
from attachments.models import Attachment
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from attachments.models import IndustrialAttachment

User = get_user_model()


class EvaluationCriteria(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    max_score = models.IntegerField(default=10)
    weight = models.FloatField(default=1.0)  # Weight for final calculation
    category = models.CharField(max_length=100, choices=[
        ('technical', 'Technical Skills'),
        ('professional', 'Professionalism'),
        ('communication', 'Communication'),
        ('task_performance', 'Task Performance'),
    ])
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} ({self.max_score} points)"
    


class SupervisorEvaluation(models.Model):
    RECOMMENDATION_CHOICES = [
        ('strongly_recommend', 'Strongly Recommend'),
        ('recommend', 'Recommend'),
        ('recommend_with_reservations', 'Recommend with Reservations'),
        ('not_recommend', 'Do Not Recommend'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
    ]

    attachment = models.ForeignKey(Attachment, on_delete=models.CASCADE)
    supervisor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    criteria_scores = models.JSONField()  # Stores scores for each criteria
    overall_rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comments = models.TextField()
    recommendation = models.CharField(max_length=50, choices=RECOMMENDATION_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")  # NEW FIELD
    evaluation_date = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['attachment', 'supervisor']
    
    def __str__(self):
        return f"Supervisor Evaluation - {self.attachment.student.username}"


# class LecturerEvaluation(models.Model):
#     GRADE_CHOICES = [
#         ('A', 'A - Excellent'),
#         ('B', 'B - Good'),
#         ('C', 'C - Satisfactory'),
#         ('D', 'D - Poor'),
#         ('F', 'F - Fail'),
#     ]

#     STATUS_CHOICES = [
#         ('draft', 'Draft'),
#         ('submitted', 'Submitted'),
#     ]
    
#     attachment = models.ForeignKey(Attachment, on_delete=models.CASCADE)
#     lecturer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
#     comments = models.TextField()
#     grade = models.CharField(max_length=1, choices=GRADE_CHOICES)
#     status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")  # NEW FIELD
#     evaluation_date = models.DateTimeField(auto_now_add=True)
    
#     class Meta:
#         unique_together = ['attachment', 'lecturer']
    
#     def __str__(self):
#         return f"Lecturer Evaluation for {self.attachment}"

class LecturerEvaluation(models.Model):
    attachment = models.ForeignKey(IndustrialAttachment, on_delete=models.CASCADE, related_name='lecturer_evaluations')
    lecturer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='evaluations_given')
    criteria = models.ForeignKey(EvaluationCriteria, on_delete=models.CASCADE)
    score = models.IntegerField()
    comments = models.TextField(blank=True)
    grade = models.CharField(max_length=2, blank=True, null=True)
    status = models.CharField(max_length=20, default="draft")
    evaluated_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['attachment', 'criteria']

    def __str__(self):
        return f"{self.attachment.student.get_full_name()} - {self.criteria.name}: {self.score}"



# class FinalAssessment(models.Model):
#     attachment = models.OneToOneField(Attachment, on_delete=models.CASCADE, related_name='final_assessment')
#     supervisor_score = models.DecimalField(max_digits=5, decimal_places=2)
#     lecturer_score = models.DecimalField(max_digits=5, decimal_places=2)
#     final_score = models.DecimalField(max_digits=5, decimal_places=2)
#     grade = models.CharField(max_length=2)
#     comments = models.TextField(blank=True)
#     assessed_by = models.ForeignKey(User, on_delete=models.CASCADE)
#     assessed_date = models.DateTimeField(auto_now_add=True)
    
#     def __str__(self):
#         return f"Final Assessment - {self.attachment.student.username}"

class FinalAssessment(models.Model):
    GRADE_CHOICES = [
        ('A', 'A - Excellent'),
        ('B', 'B - Good'),
        ('C', 'C - Satisfactory'),
        ('D', 'D - Pass'),
        ('E', 'E - Fail'),
    ]
    
    attachment = models.OneToOneField(IndustrialAttachment, on_delete=models.CASCADE, related_name='final_assessment')
    lecturer = models.ForeignKey(User, on_delete=models.CASCADE)
    overall_score = models.FloatField()
    grade = models.CharField(max_length=1, choices=GRADE_CHOICES)
    comments = models.TextField()
    assessment_date = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.attachment.student.get_full_name()} - {self.grade}"


class LogbookEvaluation(models.Model):
    logbook_entry = models.OneToOneField(
        'attachments.LogbookEntry',
        on_delete=models.CASCADE,
        related_name='evaluation'
    )
    supervisor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    score = models.PositiveIntegerField(default=3, validators=[MinValueValidator(1), MaxValueValidator(5)])
    comments = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Evaluation for {self.logbook_entry} by {self.supervisor}"
