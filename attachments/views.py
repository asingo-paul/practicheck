# attachments/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Sum
from .models import Attachment, LogbookEntry, Industry, ReportUpload,PlacementFormSubmission,Department, Lecturer, StudentAssignment
from .forms import AttachmentForm, LogbookEntryForm
import os
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Message, Announcement, User
from .models import Report
from django.db.models import Q, Count
from datetime import timedelta
from django.views.decorators.http import require_POST
import json
from django.db import models
import secrets
import string
from django.core.mail import send_mail
from django.conf import settings





def index(request):
    """Welcome page for the attachments app"""
    return HttpResponse("Welcome to Attachments App")


@login_required
def dashboard(request):
    """Student dashboard view"""
    attachments = Attachment.objects.filter(student=request.user)
    recent_entries = LogbookEntry.objects.filter(attachment__student=request.user).order_by('-entry_date')[:5]
    
    # # Get current attachment (first one or None)
    # current_attachment = attachments.first() if attachments.exists() else None
    
    context = {
        'attachments': attachments,
        # 'current_attachment': current_attachment,
        'recent_entries': recent_entries,
        "today": timezone.now().date(),
    }
    
    return render(request, 'attachments/dashboard.html', context)


# attachments/views.py
@login_required
def create_attachment(request):
    """Create a new industrial attachment - Only one allowed per user"""
    # Check if user already has an attachment
    existing_attachment = Attachment.objects.filter(student=request.user).first()
    
    if existing_attachment:
        messages.error(request, 'You can only have one industrial attachment. Please edit your existing attachment instead.')
        return redirect('attachments:edit_attachment', attachment_id=existing_attachment.id)
    
    if request.method == 'POST':
        form = AttachmentForm(request.POST)
        if form.is_valid():
            attachment = form.save(commit=False)
            attachment.student = request.user
            attachment.status = 'pending'  # Needs approval
            attachment.save()
            
            messages.success(request, 'Attachment created successfully! It will be reviewed for approval.')
            return redirect('attachments:dashboard')
    else:
        # Pre-fill with today's date and 3 months from now
        initial = {
            'start_date': timezone.now().date(),
            'end_date': timezone.now().date() + timezone.timedelta(days=90)
        }
        form = AttachmentForm(initial=initial)
    
    return render(request, 'attachments/create_attachment.html', {'form': form})


@login_required
def edit_attachment(request, attachment_id):
    """Edit an existing attachment"""
    attachment = get_object_or_404(Attachment, id=attachment_id, student=request.user)
    
    if attachment.status not in ['pending', 'approved']:
        messages.error(request, 'You can only edit pending or approved attachments.')
        return redirect('attachments:dashboard')
    
    if request.method == 'POST':
        form = AttachmentForm(request.POST, instance=attachment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Attachment updated successfully!')
            return redirect('attachments:dashboard')
    else:
        form = AttachmentForm(instance=attachment)
    
    return render(request, 'attachments/edit_attachment.html', {'form': form, 'attachment': attachment})


@login_required
def attachment_detail(request, attachment_id):
    """View attachment details"""
    attachment = get_object_or_404(Attachment, id=attachment_id)
    
    # Check if user has permission to view this attachment
    if request.user != attachment.student and not request.user.is_staff:
        messages.error(request, "You don't have permission to view this attachment.")
        return redirect('attachments:dashboard')
    
    # Get logbook entries for this attachment
    entries = LogbookEntry.objects.filter(attachment=attachment).order_by('-entry_date')[:10]
    
    # Calculate statistics
    total_hours = entries.aggregate(Sum('hours_worked'))['hours_worked__sum'] or 0
    total_entries = entries.count()
    
    context = {
        'attachment': attachment,
        'entries': entries,
        'total_hours': total_hours,
        'total_entries': total_entries,
    }
    
    return render(request, 'attachments/attachment_detail.html', context)


@login_required
def logbook_entry(request, attachment_id):
    """
    Create a daily logbook entry (only one per day).
    If an entry already exists for today, show a friendly message.
    """
    attachment = get_object_or_404(Attachment, id=attachment_id, student=request.user)
    today = timezone.now().date()

    # Check if an entry for today already exists
    existing_entry = LogbookEntry.objects.filter(attachment=attachment, entry_date=today).first()

    if existing_entry:
        messages.warning(request, "You’ve already submitted today’s entry. Please come back tomorrow to add another one.")
        return redirect('attachments:logbook', attachment_id=attachment.id)

    if request.method == 'POST':
        form = LogbookEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.attachment = attachment
            entry.entry_date = today  # force today's date
            entry.save()
            messages.success(request, 'Logbook entry saved successfully!')
            return redirect('attachments:logbook', attachment_id=attachment.id)
    else:
        form = LogbookEntryForm(initial={'entry_date': today})

    return render(request, 'attachments/logbook_entry.html', {
        'form': form,
        'attachment': attachment,
        'today': today
    })

@login_required
def logbook(request, attachment_id):
    """View logbook for a specific attachment (newest first)"""
    attachment = get_object_or_404(Attachment, id=attachment_id)
    owns_it = (
        attachment.student == request.user or
        (hasattr(request.user, 'student') and attachment.student == request.user.student)
    )
    if not (owns_it or request.user.is_staff):
        messages.error(request, "You don't have permission to view this logbook.")
        return redirect('attachments:dashboard')

    # Logbook entries
    entries = LogbookEntry.objects.filter(
        attachment=attachment
    ).order_by('-entry_date', '-id')

    # Reports uploaded
    reports = attachment.reports.all()
    reports_count = reports.count()

    # Stats
    total_hours = entries.aggregate(Sum('hours_worked'))['hours_worked__sum'] or 0
    total_entries = entries.count()
    supervisor_reviews = entries.filter(supervisor_comments__isnull=False).count()

    # Calculate progress based on actual dates
    today = timezone.now().date()
    
    if attachment.start_date and attachment.end_date:
        total_days = (attachment.end_date - attachment.start_date).days
        if today >= attachment.start_date:
            if today <= attachment.end_date:
                # Attachment is ongoing
                days_completed = (today - attachment.start_date).days
                days_remaining = (attachment.end_date - today).days
            else:
                # Attachment is completed
                days_completed = total_days
                days_remaining = 0
        else:
            # Attachment hasn't started yet
            days_completed = 0
            days_remaining = total_days
        
        progress_percentage = min(100, max(0, int((days_completed / total_days) * 100))) if total_days > 0 else 0
    else:
        # Handle cases where dates are not set
        days_completed = 0
        days_remaining = 0
        progress_percentage = 0
        total_days = 0

    context = {
        'attachment': attachment,
        'entries': entries,
        'total_hours': total_hours,
        'total_entries': total_entries,
        'supervisor_reviews': supervisor_reviews,
        'progress_percentage': progress_percentage,
        'days_remaining': days_remaining,
        'days_completed': days_completed,
        'total_days': total_days,
        'reports': reports,
        'reports_count': reports_count,
    }
    return render(request, 'attachments/logbook.html', context)






@login_required
def edit_previous_entry(request, entry_id):
    """Edit a previous logbook entry"""
    entry = get_object_or_404(LogbookEntry, id=entry_id, attachment__student=request.user)
    
    if not entry.can_edit():
        messages.error(request, 'This entry has reached the maximum number of edits (2).')
        return redirect('attachments:logbook', attachment_id=entry.attachment.id)
    
    if request.method == 'POST':
        form = LogbookEntryForm(request.POST, instance=entry)
        if form.is_valid():
            updated_entry = form.save(commit=False)
            updated_entry.edit_count += 1
            updated_entry.save()
            
            messages.success(request, 'Logbook entry updated successfully!')
            return redirect('attachments:logbook', attachment_id=entry.attachment.id)
    else:
        form = LogbookEntryForm(instance=entry)
    
    return render(request, 'attachments/logbook_entry.html', {
        'form': form,
        'entry': entry,
        'attachment': entry.attachment,
        'editing': True
    })


@login_required
def export_logbook(request, attachment_id, format_type):
    """Export logbook in various formats"""
    attachment = get_object_or_404(Attachment, id=attachment_id, student=request.user)
    entries = LogbookEntry.objects.filter(attachment=attachment).order_by('-entry_date')
    
    if format_type == 'pdf':
        # PDF export
        from django.template.loader import render_to_string
        from weasyprint import HTML
        
        html_string = render_to_string('attachments/export/logbook_pdf.html', {
            'entries': entries,
            'attachment': attachment,
            'user': request.user,
            'now': timezone.now()
        })
        
        html = HTML(string=html_string)
        pdf_file = html.write_pdf()
        
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="logbook_{attachment.organization}_{timezone.now().date()}.pdf"'
        return response
        
    elif format_type == 'csv':
        # CSV export
        import csv
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="logbook_{attachment.organization}_{timezone.now().date()}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Date', 'Department/Section', 'Tasks', 'Skills Learned', 'Achievements', 'Challenges', 'Hours Worked', 'Supervisor Comments'])
        
        for entry in entries:
            writer.writerow([
                entry.entry_date,
                entry.department_section,
                entry.tasks,
                entry.skills_learned,
                entry.achievements,
                entry.challenges,
                entry.hours_worked,
                entry.supervisor_comments
            ])
        
        return response
        
    elif format_type == 'json':
        # JSON export
        import json
        data = {
            'attachment': {
                'organization': attachment.organization,
                'department': attachment.department,
                'supervisor': attachment.supervisor_name,
                'supervisor_email': attachment.supervisor_email,
                'supervisor_phone': attachment.supervisor_phone,
                'start_date': str(attachment.start_date),
                'end_date': str(attachment.end_date),
                'status': attachment.status
            },
            'student': {
                'name': request.user.get_full_name(),
                'email': request.user.email
            },
            'entries': [
                {
                    'date': str(entry.entry_date),
                    'department_section': entry.department_section,
                    'tasks': entry.tasks,
                    'skills_learned': entry.skills_learned,
                    'achievements': entry.achievements,
                    'challenges': entry.challenges,
                    'hours_worked': float(entry.hours_worked),
                    'supervisor_comments': entry.supervisor_comments,
                    'edit_count': entry.edit_count
                }
                for entry in entries
            ]
        }
        
        response = HttpResponse(json.dumps(data, indent=2), content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="logbook_{attachment.organization}_{timezone.now().date()}.json"'
        return response
    
    return HttpResponse("Unsupported export format", status=400)


@login_required
def api_entry_detail(request, entry_id):
    """API endpoint to get entry details for modal"""
    entry = get_object_or_404(LogbookEntry, id=entry_id)
    
    # Check permission
    if request.user != entry.attachment.student and not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    data = {
        'entry_date': str(entry.entry_date),
        'department_section': entry.department_section,
        'tasks': entry.tasks,
        'skills_learned': entry.skills_learned,
        'achievements': entry.achievements,
        'challenges': entry.challenges,
        'hours_worked': float(entry.hours_worked),
        'supervisor_comments': entry.supervisor_comments,
        'edit_count': entry.edit_count,
        'created_at': entry.created_at.isoformat(),
        'updated_at': entry.updated_at.isoformat(),
    }
    
    return JsonResponse(data)




@login_required
def upload_report(request, attachment_id):
    attachment = get_object_or_404(Attachment, id=attachment_id, student=request.user)

    # # Ensure the attachment has ended before allowing uploads
    # today = timezone.now().date()
    # if attachment.end_date and today < attachment.end_date:
    #     messages.error(request, "You can only upload reports after your attachment period has ended.")
    #     return redirect("attachments:dashboard")

    # Check how many reports exist
    reports = attachment.reports.all()
    if request.method == "POST":
        if reports.count() >= 10:
            messages.error(request, "You can only upload a maximum of 5 reports.")
            return redirect("attachments:upload_report", attachment_id=attachment.id)

        report_file = request.FILES.get("report")
        if report_file:
            ext = report_file.name.split(".")[-1].lower()
            if ext not in ["pdf", "doc", "docx"]:
                messages.error(request, "Invalid file type. Only PDF, DOC, and DOCX are allowed.")
            else:
                ReportUpload.objects.create(attachment=attachment, file=report_file)
                messages.success(request, "Report uploaded successfully.")
                return redirect("attachments:upload_report", attachment_id=attachment.id)
        else:
            messages.error(request, "Please select a file to upload.")

    return render(request, "attachments/upload_report.html", {"attachment": attachment, "reports": reports})



def is_supervisor(user):
    return user.user_type == 2

@login_required
@user_passes_test(is_supervisor)
def approve_attachment(request, attachment_id):
    if request.method == 'POST':
        try:
            attachment = Attachment.objects.get(id=attachment_id, supervisor=request.user)
            attachment.status = 'active'
            attachment.approved_date = timezone.now()
            attachment.save()
            
            messages.success(request, f"Attachment for {attachment.student.get_full_name()} has been approved!")
            return JsonResponse({'success': True, 'message': 'Attachment approved successfully'})
            
        except Attachment.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Attachment not found'}, status=404)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)

@login_required
@user_passes_test(is_supervisor)
def reject_attachment(request, attachment_id):
    if request.method == 'POST':
        try:
            attachment = Attachment.objects.get(id=attachment_id)
            
            # Check if the current user is the supervisor of this attachment
            if attachment.supervisor_email != request.user.email:
                return JsonResponse({'success': False, 'error': 'You are not authorized to reject this attachment'}, status=403)
            
            attachment.status = 'cancelled'
            attachment.save()
            
            messages.success(request, f"Attachment for {attachment.student.get_full_name()} has been rejected.")
            return JsonResponse({'success': True, 'message': 'Attachment rejected successfully'})
            
        except Attachment.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Attachment not found'}, status=404)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)


@login_required
def report_upload(request, attachment_id):
    # Get latest report by student
    attachment = get_object_or_404(Attachment, id=attachment_id, student=request.user)
    report = Report.objects.filter(student=request.user).order_by('-submission_date').first()
    submissions = Report.objects.filter(student=request.user).order_by('-submission_date')

    if request.method == 'POST':
        title = request.POST.get('title')
        document = request.FILES.get('document')

        if document:
            # Increment version if report exists
            version = submissions.count() + 1
            new_report = Report.objects.create(
                student=request.user,
                attachment=attachment,
                title=title,
                document=document,
                version=version
            )
            messages.success(request, "Report submitted successfully.")
            return redirect('attachments:report_upload')

        else:
            messages.error(request, "Please upload a valid report.")

    return render(request, 'attachments/report_upload.html', {
        'report': report,
        'submissions': submissions,
        'attachment': attachment
    })


@login_required
def delete_report(request, report_id):
    report = get_object_or_404(ReportUpload, id=report_id)  # <-- ReportUpload here
    attachment_id = report.attachment.id
    report.delete()
    messages.success(request, "Report deleted successfully.")
    return redirect('attachments:logbook', attachment_id=attachment_id)


@login_required
def student_dashboard(request):
    attachments = Attachment.objects.filter(student=request.user)
    recent_entries = LogbookEntry.objects.filter(
        attachment__student=request.user
    ).order_by('-entry_date')[:5]

    return render(request, 'attachments/dashboard.html', {
        'attachments': attachments,
        'recent_entries': recent_entries,
        'today': timezone.now().date()
    })
def communication(request):
    """Industrial Attachment Placement Form"""
    
    # Get user's attachments (for sidebar)
    attachments = Attachment.objects.filter(student=request.user)
    current_attachment = attachments.first()  # Get the first attachment for sidebar
    
    # Check if user already submitted placement form for current cycle
    current_year = timezone.now().year
    existing_submission = PlacementFormSubmission.objects.filter(
        student=request.user,
        start_date__year=current_year
    ).first()
    
    if request.method == 'POST':
        if existing_submission:
            messages.error(request, 'You have already submitted the placement form for this attachment cycle.')
            return redirect('attachments:communication')
        
        try:
            # Create new placement form submission
            submission = PlacementFormSubmission(
                student=request.user,
                registration_number=request.POST.get('registration_number'),
                phone_number=request.POST.get('phone_number'),
                course_name=request.POST.get('course_name'),
                year_of_study=request.POST.get('year_of_study'),
                firm_name=request.POST.get('firm_name'),
                firm_email=request.POST.get('firm_email'),
                town_city=request.POST.get('town_city'),
                land_mark=request.POST.get('land_mark'),
                supervisor_name=request.POST.get('supervisor_name'),
                supervisor_phone=request.POST.get('supervisor_phone'),
                supervisor_email=request.POST.get('supervisor_email'),
                start_date=request.POST.get('start_date'),
                end_date=request.POST.get('end_date'),
                off_days=request.POST.getlist('off_days')  # Get all checked off days
            )
            submission.save()
            
            messages.success(request, 'Industrial Attachment Placement Form submitted successfully!')
            return redirect('attachments:communication')
            
        except Exception as e:
            messages.error(request, f'Error submitting form: {str(e)}')
    
    context = {
        'attachments': attachments,
        'current_attachment': current_attachment,
        'existing_submission': existing_submission,
    }
    
    return render(request, 'attachments/communication.html', context)

def send_message(request):
    if request.method == 'POST':
        user = request.user
        recipient_id = request.POST.get('recipient')
        subject = request.POST.get('subject', '')
        body = request.POST.get('body')
        attachment_file = request.FILES.get('attachment')

        if recipient_id and body:
            recipient = get_object_or_404(User, id=recipient_id)
            Message.objects.create(
                sender=user,
                recipient=recipient,
                subject=subject,
                body=body,
                attachment=attachment_file if attachment_file else None
            )
            # Redirect back to student communication page with active contact
            return redirect(f'/attachments/student_communication/?contact_id={recipient.id}')

    return redirect('/attachments/student_communication/')

def evaluations(request):
    # Your view logic here
    return render(request, 'attachments/assessment.html')

@login_required
def assessment(request):
    """Assessment view - placeholder for now"""
    return render(request, 'attachments/assessment.html')

# attachments/views.py - Add this function
def supervisor_logbook(request, attachment_id):
    """Supervisor view of student logbook"""
    try:
        # Get the attachment and ensure the current user is the supervisor
        attachment = get_object_or_404(Attachment, id=attachment_id)
        
        # Check if current user is the supervisor of this attachment
        if not request.user.is_authenticated or request.user.email != attachment.supervisor_email:
            return render(request, '403.html', status=403)
        
        # Get logbook entries for this attachment
        entries = LogbookEntry.objects.filter(attachment=attachment).order_by('-entry_date')
        reports = ReportUpload.objects.filter(attachment=attachment).order_by('-uploaded_at')
        
        # Calculate stats
        total_entries = entries.count()
        total_hours = sum(entry.hours_worked for entry in entries)
        supervisor_reviews = entries.filter(supervisor_comments__isnull=False).count()
        
        context = {
            'attachment': attachment,
            'entries': entries,
            'reports': reports,
            'reports_count': reports.count(),
            'total_entries': total_entries,
            'total_hours': total_hours,
            'supervisor_reviews': supervisor_reviews,
            'total_days': attachment.total_days,
        }
        
        return render(request, 'attachments/supervisor_logbook.html', context)
        
    except Exception as e:
        return render(request, 'error.html', {'error': str(e)})
    
@require_POST
def api_add_supervisor_comment(request, entry_id):
    """API endpoint for supervisors to add comments to logbook entries"""
    try:
        entry = get_object_or_404(LogbookEntry, id=entry_id)
        
        # Verify the current user is the supervisor
        if request.user.email != entry.attachment.supervisor_email:
            return JsonResponse({'error': 'Not authorized'}, status=403)
        
        data = json.loads(request.body)
        comment = data.get('comment', '').strip()
        
        if comment:
            entry.supervisor_comments = comment
            entry.save()
            
            return JsonResponse({'success': True, 'message': 'Comment added successfully'})
        else:
            return JsonResponse({'error': 'Comment cannot be empty'}, status=400)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    

def is_admin(user):
    return user.is_authenticated and (user.is_superuser or getattr(user, 'user_type', None) == 4)

@user_passes_test(is_admin)
def admin_dashboard(request):
    # Statistics
    total_students = User.objects.filter(user_type=1).count()  # Student type
    total_lecturers = Lecturer.objects.filter(is_active=True).count()
    total_placements = PlacementFormSubmission.objects.count()
    pending_placements = PlacementFormSubmission.objects.filter(status='pending').count()
    
    # Department-wise placements - SIMPLE VERSION
    departments = Department.objects.all()
    department_stats = []
    
    for dept in departments:
        total_dept_placements = PlacementFormSubmission.objects.filter(department=dept).count()
        pending_dept_placements = PlacementFormSubmission.objects.filter(
            department=dept, 
            status='pending'
        ).count()
        
        # Count assigned placements for this department
        assigned_dept_placements = StudentAssignment.objects.filter(
            placement_form__department=dept
        ).count()
        
        department_stats.append({
            'id': dept.id,
            'name': dept.name,
            'code': dept.code,
            'total_placements': total_dept_placements,
            'pending_placements': pending_dept_placements,
            'assigned_placements': assigned_dept_placements,
        })
    
    # Recent placements
    recent_placements = PlacementFormSubmission.objects.select_related(
        'student', 'department'
    ).order_by('-submitted_at')[:10]
    
    # Lecturer workload
    lecturer_workload = Lecturer.objects.filter(is_active=True).annotate(
        assigned_count=Count('assigned_students'),
        available_slots=models.F('max_students') - Count('assigned_students')
    ).order_by('department__name', 'user__first_name')
    
    context = {
        'total_students': total_students,
        'total_lecturers': total_lecturers,
        'total_placements': total_placements,
        'pending_placements': pending_placements,
        'department_stats': department_stats,
        'recent_placements': recent_placements,
        'lecturer_workload': lecturer_workload,
        'current_year': timezone.now().year,
    }
    
    return render(request, 'attachments/admin_dashboard.html', context)

@user_passes_test(is_admin)
def department_placements(request, department_id):
    department = get_object_or_404(Department, id=department_id)
    placements = PlacementFormSubmission.objects.filter(
        department=department
    ).select_related('student').prefetch_related('student_assignment')
    
    # Available lecturers in this department
    available_lecturers = Lecturer.objects.filter(
        department=department, 
        is_active=True
    ).annotate(
        assigned_count=Count('assigned_students'),
        available_slots=models.F('max_students') - Count('assigned_students')
    )
    
    context = {
        'department': department,
        'placements': placements,
        'available_lecturers': available_lecturers,
    }
    
    return render(request, 'attachments/department_placements.html', context)

@user_passes_test(is_admin)
def assign_student(request, placement_id, lecturer_id):
    placement = get_object_or_404(PlacementFormSubmission, id=placement_id)
    lecturer = get_object_or_404(Lecturer, id=lecturer_id)
    
    # Check if student already assigned for this academic year
    current_year = timezone.now().year
    existing_assignment = StudentAssignment.objects.filter(
        student=placement.student,
        academic_year=current_year
    ).exists()
    
    if existing_assignment:
        messages.error(request, 'This student is already assigned to a lecturer for this academic year.')
    else:
        # Create assignment
        assignment = StudentAssignment(
            student=placement.student,
            lecturer=lecturer,
            placement_form=placement,
            academic_year=current_year
        )
        assignment.save()
        messages.success(request, f'Student successfully assigned to {lecturer.user.get_full_name()}')
    
    return redirect('attachments:department_placements', department_id=placement.department.id)


@login_required
@user_passes_test(is_admin)
def manage_lecturers(request):
    departments = Department.objects.all()
    lecturers = Lecturer.objects.select_related('user', 'department').prefetch_related('assigned_students').all()
    
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        if form_type == 'create_lecturer':
            # Create new lecturer
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip().lower()
            staff_id = request.POST.get('staff_id', '').strip()
            department_id = request.POST.get('department')
            phone_number = request.POST.get('phone_number', '').strip()
            office_location = request.POST.get('office_location', '').strip()
            max_students = request.POST.get('max_students', 10)
            
            # Basic validation
            if not all([first_name, last_name, email, staff_id, department_id]):
                messages.error(request, 'Please fill in all required fields.')
                return redirect('attachments:manage_lecturers')
            
            try:
                # Check if email already exists
                if User.objects.filter(email=email).exists():
                    messages.error(request, 'A user with this email already exists.')
                    return redirect('attachments:manage_lecturers')
                
                # Check if staff ID already exists
                if Lecturer.objects.filter(staff_id=staff_id).exists():
                    messages.error(request, 'A lecturer with this staff ID already exists.')
                    return redirect('attachments:manage_lecturers')
                
                # Generate secure random password
                password = generate_secure_password()
                
                # Create user
                user = User.objects.create_user(
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    user_type=3  # Lecturer type
                )
                
                # Create lecturer profile
                department = Department.objects.get(id=department_id)
                lecturer = Lecturer.objects.create(
                    user=user,
                    staff_id=staff_id,
                    department=department,
                    phone_number=phone_number,
                    office_location=office_location,
                    max_students=int(max_students)
                )
                
                # Send email with login credentials
                send_lecturer_credentials(email, first_name, staff_id, password)
                
                messages.success(request, 
                    f'Lecturer {first_name} {last_name} created successfully! '
                    f'Login credentials have been sent to their email.'
                )
                
            except Exception as e:
                messages.error(request, f'Error creating lecturer: {str(e)}')
        
        elif form_type == 'update_lecturer':
            # ... (keep your existing update code) ...
            pass
    
    context = {
        'departments': departments,
        'lecturers': lecturers,
    }
    
    return render(request, 'attachments/manage_lecturers.html', context)

def generate_secure_password(length=12):
    """Generate a secure random password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        password = ''.join(secrets.choice(alphabet) for i in range(length))
        if (any(c.islower() for c in password) and 
            any(c.isupper() for c in password) and 
            any(c.isdigit() for c in password) and
            any(c in "!@#$%^&*" for c in password)):
            break
    return password

def send_lecturer_credentials(email, first_name, staff_id, password):
    """Send login credentials to lecturer via email"""
    subject = 'Your PractiCheck Lecturer Account Credentials'
    
    message = f"""
Dear {first_name},

Your lecturer account has been created on PractiCheck.

Here are your login credentials:

Staff ID: {staff_id}
Password: {password}

Login URL: {settings.SITE_URL}

Please log in and change your password immediately for security reasons.

Best regards,
PractiCheck Administration Team
"""
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

@user_passes_test(is_admin)
def toggle_lecturer(request, lecturer_id):
    try:
        lecturer = Lecturer.objects.get(id=lecturer_id)
        lecturer.is_active = not lecturer.is_active
        lecturer.save()
        
        status = "activated" if lecturer.is_active else "deactivated"
        messages.success(request, f'Lecturer {lecturer.user.get_full_name()} has been {status}.')
    
    except Lecturer.DoesNotExist:
        messages.error(request, 'Lecturer not found.')
    
    return redirect('attachments:manage_lecturers')



@login_required
@user_passes_test(is_admin)
@require_POST
def reset_lecturer_password(request, lecturer_id):
    """Reset lecturer password and send new credentials via email"""
    try:
        lecturer = Lecturer.objects.get(id=lecturer_id)
        new_password = generate_secure_password()
        
        # Update the user's password
        lecturer.user.set_password(new_password)
        lecturer.user.save()
        
        # Send email with new credentials
        send_lecturer_credentials(
            lecturer.user.email,
            lecturer.user.first_name,
            lecturer.staff_id,
            new_password
        )
        
        messages.success(request, f'Password reset successfully for {lecturer.user.get_full_name()}. New credentials sent to their email.')
        return JsonResponse({'success': True})
        
    except Lecturer.DoesNotExist:
        messages.error(request, 'Lecturer not found.')
        return JsonResponse({'success': False, 'error': 'Lecturer not found'})
    except Exception as e:
        messages.error(request, f'Error resetting password: {str(e)}')
        return JsonResponse({'success': False, 'error': str(e)})

