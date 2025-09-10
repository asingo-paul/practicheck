from django.urls import path
from . import views

app_name = "attachments"

urlpatterns = [
    path('', views.index, name='index'),
    path("dashboard/", views.dashboard, name="dashboard"),
    path('welcome/', views.welcome, name='welcome'), 
    path('logbook/<int:attachment_id>/', views.logbook, name='logbook'),
    path('report-upload/<int:attachment_id>/', views.report_upload, name='report_upload'),
    path('assessment/', views.assessment, name='assessment'),
    path('communication/', views.communication, name='communication'),
]

