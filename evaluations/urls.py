
# evaluations/urls.py
from django.urls import path
from . import views

app_name = "evaluations"

urlpatterns = [
    path("supervisor/dashboard/", views.supervisor_dashboard, name="supervisor_dashboard"),
    path('lecturer/dashboard/', views.lecturer_dashboard, name='lecturer_dashboard'),
        # Add the missing evaluation_form URL pattern
    path('evaluation-form/<int:attachment_id>/', views.evaluation_form, name='evaluation_form'),
    path('grading-panel/<int:attachment_id>/', views.grading_panel, name='grading_panel'),
    
]

