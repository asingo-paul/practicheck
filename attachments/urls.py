from django.urls import path
from . import views

app_name = 'attachments'

urlpatterns = [
    # Existing URLs
    path('', views.dashboard, name='dashboard'),
    path("dashboard/", views.student_dashboard, name="student_dashboard"),
    path('create/', views.create_attachment, name='create_attachment'),
    path('edit/<int:attachment_id>/', views.edit_attachment, name='edit_attachment'),
    path('detail/<int:attachment_id>/', views.attachment_detail, name='attachment_detail'),
    path('logbook/<int:attachment_id>/', views.logbook, name='logbook'),
    path('logbook/entry/<int:attachment_id>/', views.logbook_entry, name='logbook_entry'),
    path('logbook/edit-entry/<int:entry_id>/', views.edit_previous_entry, name='edit_logbook_entry'),
    path('export/logbook/<int:attachment_id>/<str:format_type>/', views.export_logbook, name='export_logbook'),
    path('api/entry/<int:entry_id>/', views.api_entry_detail, name='api_entry_detail'),
    path('api/entry/<int:entry_id>/comment/', views.api_add_supervisor_comment, name='api_add_supervisor_comment'),
    path("<int:attachment_id>/logbook/upload/", views.upload_report, name="upload_report"),
    path('approve/<int:attachment_id>/', views.approve_attachment, name='approve_attachment'),
    path('reject/<int:attachment_id>/', views.reject_attachment, name='reject_attachment'),
    path("upload/<int:attachment_id>/", views.upload_report, name="upload_report"),
    path('report/<int:attachment_id>/', views.report_upload, name='report_upload'),
    path('report/delete/<int:report_id>/', views.delete_report, name='delete_report'),
    path("communication/", views.communication, name="communication"),
    path('evaluations/', views.evaluations, name='evaluations'),
    path('assessment/', views.assessment, name='assessment'),
    path('supervisor/logbook/<int:attachment_id>/', views.supervisor_logbook, name='supervisor_logbook'),

    # Admin URLs
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/department/<int:department_id>/', views.department_placements, name='department_placements'),
    path('admin/assign/<int:placement_id>/<int:lecturer_id>/', views.assign_student, name='assign_student'),
    
    # Lecturer Management URLs
    path('admin/lecturers/', views.manage_lecturers, name='manage_lecturers'),
    path('admin/lecturers/<int:lecturer_id>/toggle/', views.toggle_lecturer, name='toggle_lecturer'),
    path('lecturers/<int:lecturer_id>/reset-password/', views.reset_lecturer_password, name='reset_lecturer_password'),
    
    # Students Management URLs
    path('admin/students/', views.admin_students, name='admin_students'),
    path('admin/assign-student/<int:placement_id>/', views.assign_student_to_lecturer, name='assign_student_to_lecturer'),
    path('admin/unassign-student/<int:assignment_id>/', views.unassign_student, name='unassign_student'),
    path('admin/lecturers/<int:lecturer_id>/delete/', views.delete_lecturer, name='delete_lecturer'),
    
    # Assignment URLs
    path('admin/assignments/', views.assignment_dashboard, name='assignment_dashboard'),
    path('admin/assignments/bulk-assign/', views.bulk_assign_students, name='bulk_assign_students'),
    
    # API endpoints
    path('api/departments/', views.get_departments, name='api_departments'),
    path('api/courses/', views.get_courses, name='api_courses'),
    
    # NEW: Enhanced Admin URLs
    path('admin/pending-approvals/', views.pending_approvals, name='pending_approvals'),
    path('admin/reports-dashboard/', views.reports_dashboard, name='reports_dashboard'),
    path('admin/workload-overview/', views.workload_overview, name='workload_overview'),
    path('admin/export-data/', views.export_data, name='export_data'),
    # path('admin/communication-center/', views.communication_center, name='communication_center'),
    
    # Report download URL
    path('reports/download/<int:report_id>/', views.download_report, name='download_report'),
    path('reports/student/<int:student_id>/', views.student_reports, name='student_reports'),
    
    # Student Registration URL (Add this line)
    path('admin/student-registration/', views.student_registration, name='student_registration'),

    # Auto-assignment URLs
    path('admin/auto-assign/', views.auto_assign_students, name='auto_assign_students'),
    path('admin/auto-assign-department/<int:department_id>/', views.smart_assign_department, name='smart_assign_department'),


]