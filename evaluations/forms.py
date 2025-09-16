# from django import forms
# from .models import SupervisorEvaluation, LecturerEvaluation

# class SupervisorEvaluationForm(forms.ModelForm):
#     class Meta:
#         model = SupervisorEvaluation
#         fields = '__all__'

# class LecturerEvaluationForm(forms.ModelForm):
#     class Meta:
#         model = LecturerEvaluation
#         fields = '__all__'


# evaluations/forms.py
from django import forms
from .models import SupervisorEvaluation, EvaluationCriteria
from .models import LecturerEvaluation  # Add this import

class SupervisorEvaluationForm(forms.ModelForm):
    class Meta:
        model = SupervisorEvaluation
        fields = ['comments', 'overall_rating', 'recommendation']
        widgets = {
            'comments': forms.Textarea(attrs={'rows': 4}),
            'overall_rating': forms.Select(choices=[(i, i) for i in range(1, 6)]),
            'recommendation': forms.Select(choices=SupervisorEvaluation.RECOMMENDATION_CHOICES),
        }
    
    def __init__(self, *args, **kwargs):
        # Extract criteria_list from kwargs before calling super()
        criteria_list = kwargs.pop('criteria_list', None)
        super().__init__(*args, **kwargs)
        
        # Add dynamic fields for each criteria
        if criteria_list:
            for criteria in criteria_list:
                field_name = f'criteria_{criteria.id}'
                self.fields[field_name] = forms.ChoiceField(
                    choices=[(i, i) for i in range(1, 6)],
                    label=criteria.name,
                    widget=forms.Select(attrs={'class': 'form-control'})
                )
class LecturerEvaluationForm(forms.ModelForm):
    class Meta:
        model = LecturerEvaluation
        fields = ['comments', 'grade']
        widgets = {
            'comments': forms.Textarea(attrs={'rows': 4}),
            'grade': forms.Select(choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D'), ('F', 'F')]),
        }
    
    def __init__(self, *args, **kwargs):
        # Extract criteria_list from kwargs before calling super()
        criteria_list = kwargs.pop('criteria_list', None)
        super().__init__(*args, **kwargs)
        
        # Add dynamic fields for each criteria
        if criteria_list:
            for criteria in criteria_list:
                field_name = f'criteria_{criteria.id}'
                self.fields[field_name] = forms.ChoiceField(
                    choices=[(i, i) for i in range(1, 6)],
                    label=criteria.name,
                    widget=forms.Select(attrs={'class': 'form-control'})
                )