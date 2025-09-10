from django import forms
from .models import LogbookEntry, Report

class LogbookEntryForm(forms.ModelForm):
    class Meta:
        model = LogbookEntry
        fields = '__all__'   # or list the fields you want
        

class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = '__all__'
