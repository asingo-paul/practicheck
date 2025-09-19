
# attachments/urls.py
from django.urls import path
from . import views

app_name = 'attachments'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('create/', views.create_attachment, name='create_attachment'),
    path('edit/<int:attachment_id>/', views.edit_attachment, name='edit_attachment'),
    path('detail/<int:attachment_id>/', views.attachment_detail, name='attachment_detail'),
    path('logbook/<int:attachment_id>/', views.logbook, name='logbook'),
    path('logbook/entry/<int:attachment_id>/', views.logbook_entry, name='logbook_entry'),  # This is the entry form
    path('logbook/edit-entry/<int:entry_id>/', views.edit_previous_entry, name='edit_logbook_entry'),
    path('export/logbook/<int:attachment_id>/<str:format_type>/', views.export_logbook, name='export_logbook'),
    path('api/entry/<int:entry_id>/', views.api_entry_detail, name='api_entry_detail'),
    path("<int:attachment_id>/logbook/upload/", views.upload_report, name="upload_report"),
    path('approve/<int:attachment_id>/', views.approve_attachment, name='approve_attachment'),
    # path('approve/<int:attachment_id>/', views.approve_attachment, name='approve_attachment'),
    path('reject/<int:attachment_id>/', views.reject_attachment, name='reject_attachment'),
]