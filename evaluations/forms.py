# evaluations/forms.py
from django import forms
from .models import SupervisorEvaluation, LecturerEvaluation, EvaluationCriteria


class SupervisorEvaluationForm(forms.ModelForm):
    class Meta:
        model = SupervisorEvaluation
        fields = ["comments", "overall_rating", "recommendation", "status"]
        widgets = {
            "comments": forms.Textarea(
                attrs={"rows": 4, "class": "form-control", "placeholder": "Enter feedback..."}
            ),
            "overall_rating": forms.Select(
                choices=[(i, i) for i in range(1, 6)],
                attrs={"class": "form-select"}
            ),
            "recommendation": forms.Select(
                choices=SupervisorEvaluation.RECOMMENDATION_CHOICES,
                attrs={"class": "form-select"}
            ),
            "status": forms.HiddenInput(),  # handled automatically (draft or submitted)
        }

    def __init__(self, *args, **kwargs):
        # Extract criteria_list from kwargs
        criteria_list = kwargs.pop("criteria_list", None)
        super().__init__(*args, **kwargs)

        # Add dynamic fields for each EvaluationCriteria
        if criteria_list:
            for criteria in criteria_list:
                field_name = f"criteria_{criteria.id}"
                self.fields[field_name] = forms.ChoiceField(
                    label=criteria.name,
                    choices=[(i, i) for i in range(1, 6)],
                    widget=forms.Select(attrs={"class": "form-select"})
                )


class LecturerEvaluationForm(forms.ModelForm):
    class Meta:
        model = LecturerEvaluation
        fields = ["comments", "grade", "status"]
        widgets = {
            "comments": forms.Textarea(
                attrs={"rows": 4, "class": "form-control", "placeholder": "Lecturer remarks..."}
            ),
            "grade": forms.Select(
                choices=[("A", "A"), ("B", "B"), ("C", "C"), ("D", "D"), ("F", "F")],
                attrs={"class": "form-select"}
            ),
            "status": forms.HiddenInput(),  # draft/submitted is handled in view
        }

    def __init__(self, *args, **kwargs):
        # Extract criteria_list from kwargs
        criteria_list = kwargs.pop("criteria_list", None)
        super().__init__(*args, **kwargs)

        # Add dynamic fields for EvaluationCriteria (if lecturers also grade per criteria)
        if criteria_list:
            for criteria in criteria_list:
                field_name = f"criteria_{criteria.id}"
                self.fields[field_name] = forms.ChoiceField(
                    label=criteria.name,
                    choices=[(i, i) for i in range(1, 6)],
                    widget=forms.Select(attrs={"class": "form-select"})
                )
