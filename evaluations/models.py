from django.db import models
from django.contrib.auth import get_user_model
from attachments.models import Attachment

User = get_user_model()

class EvaluationCriteria(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    max_score = models.IntegerField(default=10)
    weight = models.DecimalField(max_digits=4, decimal_places=2, default=1.0)
    
    def __str__(self):
        return self.name

class SupervisorEvaluation(models.Model):
    attachment = models.OneToOneField(Attachment, on_delete=models.CASCADE, related_name='supervisor_evaluation')
    supervisor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_evaluations')
    criteria_scores = models.JSONField()  # Stores {criteria_id: score}
    overall_score = models.DecimalField(max_digits=5, decimal_places=2)
    comments = models.TextField()
    submitted_date = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Supervisor Evaluation - {self.attachment.student.username}"

class LecturerEvaluation(models.Model):
    attachment = models.OneToOneField(Attachment, on_delete=models.CASCADE, related_name='lecturer_evaluation')
    lecturer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_lecturer_evaluations')
    criteria_scores = models.JSONField()  # Stores {criteria_id: score}
    overall_score = models.DecimalField(max_digits=5, decimal_places=2)
    comments = models.TextField()
    submitted_date = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Lecturer Evaluation - {self.attachment.student.username}"

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