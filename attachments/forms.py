# attachments/forms.py
from django import forms
from .models import Attachment, LogbookEntry, Industry
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
# from .models import Report

class AttachmentForm(forms.ModelForm):
    class Meta:
        model = Attachment
        fields = ['organization', 'department', 'supervisor_name', 'supervisor_email', 
                 'supervisor_phone', 'start_date', 'end_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'organization': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company/Organization name'}),
            'department': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Department/Section'}),
            'supervisor_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name'}),
            'supervisor_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
            'supervisor_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if start_date > end_date:
                raise forms.ValidationError("End date cannot be before start date.")
            
            if start_date < timezone.now().date():
                raise forms.ValidationError("Start date cannot be in the past.")
            
            # Ensure attachment is at least 30 days
            min_duration = (end_date - start_date).days
            if min_duration < 30:
                raise forms.ValidationError("Attachment must be at least 30 days long.")
            
            # Ensure attachment doesn't exceed 1 year
            if min_duration > 365:
                raise forms.ValidationError("Attachment cannot exceed 1 year.")
        
        return cleaned_data
        
class LogbookEntryForm(forms.ModelForm):
    class Meta:
        model = LogbookEntry
        fields = ['entry_date', 'department_section', 'tasks', 'skills_learned', 
                 'achievements', 'challenges', 'hours_worked']
        widgets = {
            'entry_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'department_section': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., IT Department, Marketing Section'}),
            'tasks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe the tasks you worked on today...'}),
            'skills_learned': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'What new skills or knowledge did you gain today?...'}),
            'achievements': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Any notable achievements or accomplishments...'}),
            'challenges': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Challenges faced and how you addressed them...'}),
            'hours_worked': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'min': '0.5', 'max': '24'}),
        }
    
    def clean_entry_date(self):
        entry_date = self.cleaned_data['entry_date']
        if entry_date > timezone.now().date():
            raise forms.ValidationError("Entry date cannot be in the future.")
        return entry_date


# from .models import LogbookEntry, Report
# 
# class LogbookEntryForm(forms.ModelForm):
#     class Meta:
#         model = LogbookEntry
#         fields = '__all__'   # or list the fields you want
#         
# 
# class ReportForm(forms.ModelForm):
#     class Meta:
#         model = Report
#         fields = '__all__'