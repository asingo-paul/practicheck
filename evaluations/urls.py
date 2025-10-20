# evaluations/urls.py
from django.urls import path, include
from . import views
from django.contrib import admin

app_name = "evaluations"

urlpatterns = [
    # Supervisor URLs
    path("supervisor/dashboard/", views.supervisor_dashboard, name="supervisor_dashboard"),
    path("supervisor/student/<int:attachment_id>/logbooks/", views.student_logbooks, name="student_logbooks"),
    path("supervisor/logbook/<int:logbook_id>/evaluate/", views.evaluate_logbook, name="evaluate_logbook"),
    path("supervisor/evaluate/<int:attachment_id>/", views.evaluation_form, name="evaluation_form"),

    # Lecturer URLs
    path("lecturer/dashboard/", views.lecturer_dashboard, name="lecturer_dashboard"),
    path("lecturer/grading-panel/<int:attachment_id>/", views.grading_panel, name="grading_panel"),

    path('lecturer/results/<int:attachment_id>/', views.evaluation_results, name='evaluation_results'),
    
]
