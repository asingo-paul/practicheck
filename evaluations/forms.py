from django import forms
from .models import SupervisorEvaluation, LecturerEvaluation

class SupervisorEvaluationForm(forms.ModelForm):
    class Meta:
        model = SupervisorEvaluation
        fields = '__all__'

class LecturerEvaluationForm(forms.ModelForm):
    class Meta:
        model = LecturerEvaluation
        fields = '__all__'
