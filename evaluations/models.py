from django.db import models
from django.contrib.auth import get_user_model
from attachments.models import Attachment
from django.conf import settings

User = get_user_model()

class EvaluationCriteria(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    max_score = models.IntegerField(default=10)
    weight = models.DecimalField(max_digits=4, decimal_places=2, default=1.0)
    
    def __str__(self):
        return self.name

class SupervisorEvaluation(models.Model):
    # Add this choices definition
    RECOMMENDATION_CHOICES = [
        ('strongly_recommend', 'Strongly Recommend'),
        ('recommend', 'Recommend'),
        ('recommend_with_reservations', 'Recommend with Reservations'),
        ('not_recommend', 'Do Not Recommend'),
    ]

    # attachment = models.OneToOneField(Attachment, on_delete=models.CASCADE, related_name='supervisor_evaluation')
    # supervisor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_evaluations')
    # criteria_scores = models.JSONField()  # Stores {criteria_id: score}
    # overall_score = models.DecimalField(max_digits=5, decimal_places=2)
    # comments = models.TextField()
    # submitted_date = models.DateTimeField(auto_now_add=True)
    attachment = models.ForeignKey(Attachment, on_delete=models.CASCADE)
    supervisor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    criteria_scores = models.JSONField()  # Stores scores for each criteria
    overall_rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comments = models.TextField()
    recommendation = models.CharField(max_length=50, choices=RECOMMENDATION_CHOICES)
    evaluation_date = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['attachment', 'supervisor']
    
    def __str__(self):
        return f"Evaluation for {self.attachment} by {self.supervisor}"
    
    def __str__(self):
        return f"Supervisor Evaluation - {self.attachment.student.username}"

# class LecturerEvaluation(models.Model):
#     attachment = models.OneToOneField(Attachment, on_delete=models.CASCADE, related_name='lecturer_evaluation')
#     lecturer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_lecturer_evaluations')
#     criteria_scores = models.JSONField()  # Stores {criteria_id: score}
#     overall_score = models.DecimalField(max_digits=5, decimal_places=2)
#     comments = models.TextField()
#     submitted_date = models.DateTimeField(auto_now_add=True)
    
#     def __str__(self):
#         return f"Lecturer Evaluation - {self.attachment.student.username}"

# evaluations/models.py - add this after SupervisorEvaluation
class LecturerEvaluation(models.Model):
    GRADE_CHOICES = [
        ('A', 'A - Excellent'),
        ('B', 'B - Good'),
        ('C', 'C - Satisfactory'),
        ('D', 'D - Poor'),
        ('F', 'F - Fail'),
    ]
    
    attachment = models.ForeignKey(Attachment, on_delete=models.CASCADE)
    lecturer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    comments = models.TextField()
    # grade = models.CharField(max_length=1, choices=GRADE_CHOICES, null=True, blank=True)
    grade = models.CharField(max_length=1, choices=GRADE_CHOICES)
    evaluation_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['attachment', 'lecturer']
    
    def __str__(self):
        return f"Lecturer Evaluation for {self.attachment}"

class FinalAssessment(models.Model):
    attachment = models.OneToOneField(Attachment, on_delete=models.CASCADE, related_name='final_assessment')
    supervisor_score = models.DecimalField(max_digits=5, decimal_places=2)
    lecturer_score = models.DecimalField(max_digits=5, decimal_places=2)
    final_score = models.DecimalField(max_digits=5, decimal_places=2)
    grade = models.CharField(max_length=2)
    comments = models.TextField(blank=True)
    assessed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    assessed_date = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Final Assessment - {self.attachment.student.username}"
