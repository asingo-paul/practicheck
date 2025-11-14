# attachments/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Sum
from .models import Attachment, LogbookEntry, Industry, ReportUpload, PlacementFormSubmission, Department, Lecturer, StudentAssignment
from .forms import AttachmentForm, LogbookEntryForm
import os
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Message, Announcement, User
from .models import Report, Course
from django.db.models import Q, Count
from datetime import timedelta
from django.views.decorators.http import require_POST
import json
from django.db import models
import secrets
import string
from django.core.mail import send_mail
from django.conf import settings
from .email_utils import send_lecturer_credentials, send_lecturer_password_reset
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

import csv
from django.template.loader import render_to_string
from weasyprint import HTML
import io
from django.core.mail import send_mass_mail
from django.db.models import Count, Q, Avg, Sum
from datetime import datetime, timedelta

def index(request):
    """Welcome page for the attachments app"""
    return HttpResponse("Welcome to Attachments App")

@login_required
def dashboard(request):
    """Student dashboard view"""
    attachments = Attachment.objects.filter(student=request.user)
    recent_entries = LogbookEntry.objects.filter(attachment__student=request.user).order_by('-entry_date')[:5]
    
    context = {
        'attachments': attachments,
        'recent_entries': recent_entries,
        "today": timezone.now().date(),
    }
    
    return render(request, 'attachments/dashboard.html', context)

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
        messages.warning(request, "You've already submitted today's entry. Please come back tomorrow to add another one.")
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
    
    # Calculate statistics
    entries_with_comments = entries.filter(supervisor_comments__isnull=False).count()
    total_hours = entries.aggregate(Sum('hours_worked'))['hours_worked__sum'] or 0
    
    # Calculate additional statistics for PDF
    progress_percentage = attachment.progress_percentage
    if entries.count() > 0:
        average_hours_per_day = total_hours / entries.count()
    else:
        average_hours_per_day = 0
    
    if entries.count() > 0:
        reviewed_percentage = (entries_with_comments / entries.count()) * 100
    else:
        reviewed_percentage = 0
    
    # Get university and department information
    university_name = "Machakos University"  # Default, you can make this dynamic
    department_name = None
    course_name = None
    academic_year = "2024/2025"  # Default, you can make this dynamic
    
    # Get user's department and course if available
    if hasattr(request.user, 'department') and request.user.department:
        department_name = request.user.department.name
        university_name = getattr(request.user.department, 'university', university_name)
    
    if hasattr(request.user, 'course') and request.user.course:
        course_name = request.user.course.name
    
    # Get academic year from student assignments or user profile
    if hasattr(request.user, 'student_assignments') and request.user.student_assignments.exists():
        assignment = request.user.student_assignments.first()
        academic_year = assignment.academic_year
    
    # Get lecturer name if assigned
    lecturer_name = None
    if hasattr(request.user, 'student_assignments') and request.user.student_assignments.exists():
        assignment = request.user.student_assignments.first()
        lecturer_name = assignment.lecturer.user.get_full_name()
    
    if format_type == 'pdf':
        # PDF export with enhanced layout including university info
        html_string = render_to_string('attachments/export/logbook_pdf.html', {
            'entries': entries,
            'attachment': attachment,
            'user': request.user,
            'now': timezone.now(),
            'total_hours': total_hours,
            'entries_with_comments': entries_with_comments,
            'progress_percentage': progress_percentage,
            'average_hours_per_day': average_hours_per_day,
            'reviewed_percentage': reviewed_percentage,
            'lecturer_name': lecturer_name,
            'university_name': university_name,
            'department_name': department_name,
            'course_name': course_name,
            'academic_year': academic_year,
        })
        
        html = HTML(string=html_string)
        pdf_file = html.write_pdf()
        
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{university_name.replace(" ", "_")}_Logbook_{attachment.organization}_{timezone.now().date()}.pdf"'
        return response
        
    elif format_type == 'csv':
        # CSV export - UPDATED to include university info
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{university_name.replace(" ", "_")}_Logbook_{attachment.organization}_{timezone.now().date()}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['University', 'Department', 'Student Name', 'Registration Number', 'Entry #', 'Date', 
                        'Department/Section', 'Tasks', 'Skills Learned', 'Achievements', 'Challenges', 
                        'Hours Worked', 'Supervisor Comments', 'Has Comments'])
        
        for i, entry in enumerate(entries, 1):
            writer.writerow([
                university_name,
                department_name or '',
                request.user.get_full_name(),
                request.user.student_id or '',
                i,
                entry.entry_date,
                entry.department_section,
                entry.tasks,
                entry.skills_learned,
                entry.achievements,
                entry.challenges,
                entry.hours_worked,
                entry.supervisor_comments,
                'Yes' if entry.supervisor_comments else 'No'
            ])
        
        return response
        
    elif format_type == 'json':
        # JSON export - UPDATED to include university info
        data = {
            'academic_institution': {
                'university': university_name,
                'department': department_name,
                'course': course_name,
                'academic_year': academic_year,
            },
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
                'email': request.user.email,
                'student_id': request.user.student_id
            },
            'lecturer': lecturer_name,
            'statistics': {
                'total_entries': entries.count(),
                'total_hours': float(total_hours),
                'entries_with_comments': entries_with_comments,
                'progress_percentage': progress_percentage,
                'average_hours_per_day': float(average_hours_per_day),
                'reviewed_percentage': float(reviewed_percentage)
            },
            'entries': [
                {
                    'entry_number': i,
                    'date': str(entry.entry_date),
                    'department_section': entry.department_section,
                    'tasks': entry.tasks,
                    'skills_learned': entry.skills_learned,
                    'achievements': entry.achievements,
                    'challenges': entry.challenges,
                    'hours_worked': float(entry.hours_worked),
                    'supervisor_comments': entry.supervisor_comments,
                    'has_comments': bool(entry.supervisor_comments),
                    'edit_count': entry.edit_count
                }
                for i, entry in enumerate(entries, 1)
            ]
        }
        
        response = HttpResponse(json.dumps(data, indent=2), content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="{university_name.replace(" ", "_")}_Logbook_{attachment.organization}_{timezone.now().date()}.json"'
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

    # Check how many reports exist
    reports = attachment.reports.all()
    if request.method == "POST":
        if reports.count() >= 10:
            messages.error(request, "You can only upload a maximum of 10 reports.")
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
    report = get_object_or_404(ReportUpload, id=report_id)
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
    current_attachment = attachments.first()
    
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
                off_days=request.POST.getlist('off_days')
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
            return redirect(f'/attachments/student_communication/?contact_id={recipient.id}')

    return redirect('/attachments/student_communication/')

def evaluations(request):
    return render(request, 'attachments/assessment.html')

@login_required
def assessment(request):
    """Assessment view - placeholder for now"""
    return render(request, 'attachments/assessment.html')

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
                
                # Send email with login credentials using the new function
                email_sent = send_lecturer_credentials(email, first_name, staff_id, password)
                
                if email_sent:
                    messages.success(request, 
                        f'Lecturer {first_name} {last_name} created successfully! '
                        f'Login credentials have been sent to their email.'
                    )
                else:
                    messages.warning(request, 
                        f'Lecturer {first_name} {last_name} created successfully, '
                        f'but failed to send email. Please provide these credentials manually:<br>'
                        f'Staff ID: <strong>{staff_id}</strong><br>'
                        f'Password: <strong>{password}</strong>'
                    )
                
            except Exception as e:
                messages.error(request, f'Error creating lecturer: {str(e)}')
        
        elif form_type == 'update_lecturer':
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
        email_sent = send_lecturer_password_reset(
            lecturer.user.email,
            lecturer.user.first_name,
            lecturer.staff_id,
            new_password
        )
        
        if email_sent:
            messages.success(request, f'Password reset successfully for {lecturer.user.get_full_name()}. New credentials sent to their email.')
        else:
            messages.warning(request, 
                f'Password reset for {lecturer.user.get_full_name()} but email failed. '
                f'Please provide these credentials manually:<br>'
                f'New Password: <strong>{new_password}</strong>'
            )
            
        return JsonResponse({'success': True})
        
    except Lecturer.DoesNotExist:
        messages.error(request, 'Lecturer not found.')
        return JsonResponse({'success': False, 'error': 'Lecturer not found'})
    except Exception as e:
        messages.error(request, f'Error resetting password: {str(e)}')
        return JsonResponse({'success': False, 'error': str(e)})

@user_passes_test(is_admin)
def admin_dashboard(request):
    # Statistics - Count ALL students (registered users with user_type=1)
    total_students = User.objects.filter(user_type=1).count()
    total_lecturers = Lecturer.objects.filter(is_active=True).count()
    total_placements = PlacementFormSubmission.objects.count()
    
    # Assignment statistics - Count students with assignments
    assigned_students_count = StudentAssignment.objects.values('student').distinct().count()
    unassigned_students_count = total_students - assigned_students_count
    
    # Pending approvals
    pending_approvals_count = PlacementFormSubmission.objects.filter(status='pending').count() + \
                            Attachment.objects.filter(status='pending').count()
    
    # Recent reports (last 7 days)
    new_reports_count = ReportUpload.objects.filter(
        uploaded_at__gte=timezone.now() - timedelta(days=7)
    ).count()
    
    # Student growth (compared to last month)
    last_month = timezone.now() - timedelta(days=30)
    students_last_month = User.objects.filter(
        user_type=1, date_joined__lt=last_month
    ).count()
    student_growth = round(((total_students - students_last_month) / students_last_month * 100), 1) if students_last_month > 0 else 0
    
    # Available slots
    available_slots = Lecturer.objects.filter(is_active=True).aggregate(
        total_slots=Sum('max_students'),
        used_slots=Count('assigned_students')
    )
    available_slots_count = (available_slots['total_slots'] or 0) - (available_slots['used_slots'] or 0)
    
    # Assignment rate
    assignment_rate = round((assigned_students_count / total_students * 100), 1) if total_students > 0 else 0
    
    # Department-wise statistics
    departments = Department.objects.all()
    department_stats = []
    
    for dept in departments:
        # Count all students in this department
        total_dept_students = User.objects.filter(
            user_type=1, 
            department=dept
        ).count()
        
        # Count assigned students in this department
        assigned_dept_students = StudentAssignment.objects.filter(
            student__department=dept
        ).values('student').distinct().count()
        
        # Calculate unassigned
        unassigned_dept_students = total_dept_students - assigned_dept_students
        
        # Recent reports in this department
        recent_reports = ReportUpload.objects.filter(
            attachment__student__department=dept,
            uploaded_at__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        # Assignment rate
        dept_assignment_rate = round((assigned_dept_students / total_dept_students * 100), 1) if total_dept_students > 0 else 0
        
        department_stats.append({
            'id': dept.id,
            'name': dept.name,
            'code': dept.code,
            'total_placements': total_dept_students,
            'assigned_placements': assigned_dept_students,
            'unassigned_placements': unassigned_dept_students,
            'recent_reports': recent_reports,
            'assignment_rate': dept_assignment_rate,
        })
    
    # Recent placements (actual placement submissions)
    recent_placements = PlacementFormSubmission.objects.select_related(
        'student', 'department'
    ).prefetch_related('student_assignments').order_by('-submitted_at')[:10]
    
    # Lecturer workload
    lecturer_workload = Lecturer.objects.filter(is_active=True).annotate(
        assigned_count=Count('assigned_students'),
        available_slots=models.F('max_students') - Count('assigned_students')
    ).order_by('department__name', 'user__first_name')
    
    # Quick assignment data - Show unassigned STUDENTS (not placements)
    unassigned_students = User.objects.filter(
        user_type=1,
        student_assignments__isnull=True
    ).select_related('department')[:10]
    
    recent_assignments = StudentAssignment.objects.select_related(
        'student', 'lecturer', 'lecturer__user'
    ).order_by('-assigned_date')[:5]
    
    # Recent activities (simplified version)
    recent_activities = []
    
    # System notifications
    system_notifications = [
        {
            'title': 'System Running',
            'message': 'All systems operational',
            'priority': 'success',
            'icon': 'check-circle',
            'timestamp': timezone.now() - timedelta(hours=1),
            'action_url': None
        }
    ]
    
    context = {
        'total_students': total_students,
        'total_lecturers': total_lecturers,
        'total_placements': total_placements,
        'assigned_students_count': assigned_students_count,
        'unassigned_students_count': unassigned_students_count,
        'pending_approvals_count': pending_approvals_count,
        'new_reports_count': new_reports_count,
        'student_growth': student_growth,
        'available_slots': available_slots_count,
        'assignment_rate': assignment_rate,
        'department_stats': department_stats,
        'recent_placements': recent_placements,
        'lecturer_workload': lecturer_workload,
        'unassigned_students': unassigned_students,
        'recent_assignments': recent_assignments,
        'recent_activities': recent_activities,
        'system_notifications': system_notifications,
        'notifications_count': len(system_notifications),
        'system_health': 'healthy',
        'last_check': timezone.now().strftime('%H:%M'),
        'current_date': timezone.now().strftime('%B %d, %Y'),
    }
    
    return render(request, 'attachments/admin_dashboard.html', context)

@user_passes_test(is_admin)
def admin_students(request):
    """Admin view for managing all students and their assignments"""
    # Get filter parameters
    assignment_filter = request.GET.get('filter', 'all')
    department_filter = request.GET.get('department', '')
    year_filter = request.GET.get('year', '')
    
    # Get ALL registered students (users with user_type=1)
    students = User.objects.filter(user_type=1).select_related(
        'department', 'course'
    ).prefetch_related(
        'student_assignments',
        'student_assignments__lecturer',
        'student_assignments__lecturer__user',
    ).order_by('first_name', 'last_name')
    
    # Apply filters
    if assignment_filter == 'assigned':
        students = students.filter(student_assignments__isnull=False)
    elif assignment_filter == 'unassigned':
        students = students.filter(student_assignments__isnull=True)
    
    if department_filter:
        students = students.filter(department_id=department_filter)
    
    if year_filter:
        students = students.filter(year_of_study=year_filter)
    
    # Get departments for filter dropdown
    departments = Department.objects.all()
    
    # Statistics - Calculate based on ALL students
    total_students = students.count()
    assigned_count = students.filter(student_assignments__isnull=False).count()
    unassigned_count = students.filter(student_assignments__isnull=True).count()
    
    # Calculate assignment rate
    assignment_rate = (assigned_count / total_students * 100) if total_students > 0 else 0
    
    # Get placement forms separately to avoid the prefetch error
    student_ids = students.values_list('id', flat=True)
    placement_forms = PlacementFormSubmission.objects.filter(
        student_id__in=student_ids
    ).select_related('student')
    
    # Get student reports for the modal
    student_reports = ReportUpload.objects.filter(
        attachment__student_id__in=student_ids
    ).select_related('attachment')
    
    # Create dictionaries for quick lookup
    placement_forms_by_student = {}
    for placement in placement_forms:
        if placement.student_id not in placement_forms_by_student:
            placement_forms_by_student[placement.student_id] = []
        placement_forms_by_student[placement.student_id].append(placement)
    
    student_reports_by_student = {}
    for report in student_reports:
        if report.attachment.student_id not in student_reports_by_student:
            student_reports_by_student[report.attachment.student_id] = []
        student_reports_by_student[report.attachment.student_id].append(report)
    
    # Group students by year and course for grouped view
    grouped_students = []
    years = students.values_list('year_of_study', flat=True).distinct().order_by('year_of_study')
    
    for year in years:
        year_students = students.filter(year_of_study=year)
        year_courses = []
        
        # Get distinct courses for this year
        courses = Course.objects.filter(
            id__in=year_students.values_list('course_id', flat=True).distinct()
        )
        
        for course in courses:
            course_students = year_students.filter(course=course)
            year_courses.append({
                'course': course,
                'students': course_students,
                'students_count': course_students.count()
            })
        
        grouped_students.append({
            'year': year,
            'courses': year_courses,
            'students_count': year_students.count()
        })
    
    context = {
        'students': students,
        'departments': departments,
        'placement_forms_by_student': placement_forms_by_student,
        'student_reports_by_student': student_reports_by_student,
        'grouped_students': grouped_students,
        'total_students': total_students,
        'assigned_count': assigned_count,
        'unassigned_count': unassigned_count,
        'assignment_rate': assignment_rate,
        'current_filter': assignment_filter,
        'selected_department': department_filter,
        'selected_year': year_filter,
    }
    
    return render(request, 'attachments/admin_students.html', context)

@user_passes_test(is_admin)
def department_placements(request, department_id):
    department = get_object_or_404(Department, id=department_id)
    
    # Get ALL students in this department (not just placements)
    students = User.objects.filter(
        user_type=1,
        department=department
    ).select_related('course').prefetch_related(
        'student_assignments',
        'student_assignments__lecturer',
        'student_assignments__lecturer__user',
        'placement_forms'
    ).order_by('first_name', 'last_name')
    
    # Available lecturers in this department
    available_lecturers = Lecturer.objects.filter(
        department=department, 
        is_active=True
    ).annotate(
        assigned_count=Count('assigned_students'),
        available_slots=models.F('max_students') - Count('assigned_students')
    ).select_related('user')
    
    context = {
        'department': department,
        'students': students,
        'available_lecturers': available_lecturers,
    }
    
    return render(request, 'attachments/department_placements.html', context)

@user_passes_test(is_admin)
@require_POST
def assign_student_to_lecturer(request, student_id):
    """Assign a student to a lecturer from the modal form"""
    student = get_object_or_404(User, id=student_id, user_type=1)
    lecturer_id = request.POST.get('lecturer_id')
    
    if not lecturer_id:
        messages.error(request, 'Please select a lecturer.')
        return redirect('attachments:admin_students')
    
    lecturer = get_object_or_404(Lecturer, id=lecturer_id)
    
    # Check if student already assigned for this academic year
    current_year = timezone.now().year
    existing_assignment = StudentAssignment.objects.filter(
        student=student,
        academic_year=current_year
    ).exists()
    
    if existing_assignment:
        messages.error(request, 'This student is already assigned to a lecturer for this academic year.')
    else:
        # Check if lecturer has available slots
        assigned_count = StudentAssignment.objects.filter(lecturer=lecturer).count()
        if assigned_count >= lecturer.max_students:
            messages.error(request, f'Lecturer {lecturer.user.get_full_name()} has reached maximum student capacity.')
        else:
            # Get the student's latest placement form (if any)
            placement_form = student.placement_forms.first()
            
            # Create assignment
            assignment = StudentAssignment(
                student=student,
                lecturer=lecturer,
                placement_form=placement_form,
                academic_year=current_year
            )
            assignment.save()
            messages.success(request, 
                f'Student {student.get_full_name()} successfully assigned to {lecturer.user.get_full_name()}'
            )
    
    return redirect('attachments:admin_students')

@user_passes_test(is_admin)
def assign_student(request, student_id, lecturer_id):
    """Quick assign student to lecturer (from department placements page)"""
    student = get_object_or_404(User, id=student_id, user_type=1)
    lecturer = get_object_or_404(Lecturer, id=lecturer_id)
    
    # Check if student already assigned for this academic year
    current_year = timezone.now().year
    existing_assignment = StudentAssignment.objects.filter(
        student=student,
        academic_year=current_year
    ).exists()
    
    if existing_assignment:
        messages.error(request, 'This student is already assigned to a lecturer for this academic year.')
    else:
        # Check if lecturer has available slots
        assigned_count = StudentAssignment.objects.filter(lecturer=lecturer).count()
        if assigned_count >= lecturer.max_students:
            messages.error(request, f'Lecturer {lecturer.user.get_full_name()} has reached maximum student capacity.')
        else:
            # Get or create placement form for this student
            placement_form = PlacementFormSubmission.objects.filter(student=student).first()
            
            # Create assignment
            assignment = StudentAssignment(
                student=student,
                lecturer=lecturer,
                placement_form=placement_form,
                academic_year=current_year
            )
            assignment.save()
            
            messages.success(request, 
                f'Student {student.get_full_name()} successfully assigned to {lecturer.user.get_full_name()}'
            )
    
    return redirect('attachments:department_placements', department_id=student.department.id)

@user_passes_test(is_admin)
@require_POST
def unassign_student(request, assignment_id):
    """Remove student assignment"""
    assignment = get_object_or_404(StudentAssignment, id=assignment_id)
    student_name = assignment.student.get_full_name()
    assignment.delete()
    
    messages.success(request, f'Assignment removed for {student_name}.')
    return redirect('attachments:admin_students')

@user_passes_test(is_admin)
@require_POST
def delete_lecturer(request, lecturer_id):
    """Delete a lecturer and their associated user account"""
    try:
        lecturer = Lecturer.objects.get(id=lecturer_id)
        user = lecturer.user
        lecturer_name = lecturer.user.get_full_name()
        
        # Check if lecturer has assigned students
        if lecturer.assigned_students.exists():
            messages.error(request, 
                f'Cannot delete {lecturer_name} because they have assigned students. '
                f'Please reassign or unassign the students first.'
            )
        else:
            # Delete the lecturer and associated user
            lecturer.delete()
            user.delete()
            messages.success(request, f'Lecturer {lecturer_name} has been deleted successfully.')
    
    except Lecturer.DoesNotExist:
        messages.error(request, 'Lecturer not found.')
    
    return redirect('attachments:manage_lecturers')

@user_passes_test(is_admin)
def assignment_dashboard(request):
    """Dedicated page for assigning students to lecturers"""
    # Get all unassigned STUDENTS (not placements)
    unassigned_students = User.objects.filter(
        user_type=1,
        student_assignments__isnull=True
    ).select_related('department', 'course').order_by('department__name', 'first_name')
    
    # Get all active lecturers with their available slots
    lecturers = Lecturer.objects.filter(is_active=True).annotate(
        assigned_count=Count('assigned_students'),
        available_slots=models.F('max_students') - Count('assigned_students')
    ).select_related('user', 'department').order_by('department__name', 'user__first_name')
    
    # Group students by department
    students_by_department = {}
    for student in unassigned_students:
        dept_name = student.department.name if student.department else "No Department"
        if dept_name not in students_by_department:
            students_by_department[dept_name] = []
        students_by_department[dept_name].append(student)
    
    # Group lecturers by department (only show those with available slots)
    lecturers_by_department = {}
    for lecturer in lecturers:
        if lecturer.available_slots > 0:
            dept_name = lecturer.department.name
            if dept_name not in lecturers_by_department:
                lecturers_by_department[dept_name] = []
            lecturers_by_department[dept_name].append(lecturer)
    
    context = {
        'students_by_department': students_by_department,
        'lecturers_by_department': lecturers_by_department,
        'total_unassigned': unassigned_students.count(),
        'total_lecturers': sum(len(lecturers) for lecturers in lecturers_by_department.values()),
    }
    
    return render(request, 'attachments/assignment_dashboard.html', context)

@user_passes_test(is_admin)
@require_POST
def bulk_assign_students(request):
    """Bulk assign students to lecturers"""
    assignments = request.POST.getlist('assignments')
    assigned_count = 0
    errors = []
    
    current_year = timezone.now().year
    
    for assignment_str in assignments:
        if not assignment_str:
            continue
            
        try:
            student_id, lecturer_id = assignment_str.split('_')
            student = User.objects.get(id=student_id, user_type=1)
            lecturer = Lecturer.objects.get(id=lecturer_id)
            
            # Check if student already assigned for this academic year
            existing_assignment = StudentAssignment.objects.filter(
                student=student,
                academic_year=current_year
            ).exists()
            
            if existing_assignment:
                errors.append(f"{student.get_full_name()} is already assigned")
                continue
            
            # Check if lecturer has available slots
            assigned_count_current = StudentAssignment.objects.filter(lecturer=lecturer).count()
            if assigned_count_current >= lecturer.max_students:
                errors.append(f"{lecturer.user.get_full_name()} has no available slots for {student.get_full_name()}")
                continue
            
            # Find placement form by direct query (most reliable)
            placement_form = PlacementFormSubmission.objects.filter(student=student).first()
            
            # Create assignment
            StudentAssignment.objects.create(
                student=student,
                lecturer=lecturer,
                placement_form=placement_form,
                academic_year=current_year
            )
            assigned_count += 1
            
        except (ValueError, User.DoesNotExist, Lecturer.DoesNotExist):
            errors.append("Invalid assignment data")
            continue
    
    if assigned_count > 0:
        messages.success(request, f'Successfully assigned {assigned_count} student(s).')
    if errors:
        messages.error(request, f'Could not assign {len(errors)} student(s): {", ".join(errors[:5])}')
    
    return redirect('attachments:assignment_dashboard')

def get_departments(request):
    """API endpoint to get departments for a university"""
    university = request.GET.get('university', 'Machakos University')
    departments = Department.objects.filter(university=university).values('id', 'name', 'code')
    return JsonResponse(list(departments), safe=False)

def get_courses(request):
    """API endpoint to get courses for a department"""
    department_id = request.GET.get('department_id')
    if department_id:
        courses = Course.objects.filter(department_id=department_id, is_active=True).values('id', 'name', 'code')
        return JsonResponse(list(courses), safe=False)
    return JsonResponse([], safe=False)

@login_required
@user_passes_test(is_admin)
def toggle_lecturer(request, lecturer_id):
    """Activate/Deactivate lecturer account"""
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
def download_report(request, report_id):
    """Download a report file"""
    report = get_object_or_404(ReportUpload, id=report_id)
    
    # Check permissions - student can download their own reports, admin can download all
    if request.user != report.attachment.student and not request.user.is_staff:
        messages.error(request, "You don't have permission to download this report.")
        return redirect('attachments:dashboard')
    
    response = HttpResponse(report.file, content_type='application/octet-stream')
    response['Content-Disposition'] = f'attachment; filename="{report.file.name}"'
    return response

@user_passes_test(is_admin)
def student_reports(request, student_id):
    """Admin view of all reports for a specific student"""
    student = get_object_or_404(User, id=student_id, user_type=1)
    reports = ReportUpload.objects.filter(attachment__student=student).select_related('attachment')
    
    context = {
        'student': student,
        'reports': reports,
    }
    
    return render(request, 'attachments/student_reports.html', context)

@user_passes_test(is_admin)
def pending_approvals(request):
    """View all pending approvals"""
    pending_placements = PlacementFormSubmission.objects.filter(status='pending').select_related(
        'student', 'department'
    )
    pending_attachments = Attachment.objects.filter(status='pending').select_related('student')
    
    context = {
        'pending_placements': pending_placements,
        'pending_attachments': pending_attachments,
        'pending_approvals_count': pending_placements.count() + pending_attachments.count(),
    }
    return render(request, 'attachments/pending_approvals.html', context)

@user_passes_test(is_admin)
def reports_dashboard(request):
    """Comprehensive reports dashboard"""
    # Get filter parameters
    department_filter = request.GET.get('department', '')
    date_filter = request.GET.get('date_range', 'all')
    page = request.GET.get('page', 1)
    
    # Base queryset
    reports = ReportUpload.objects.select_related(
        'attachment', 'attachment__student', 'attachment__student__department'
    ).order_by('-uploaded_at')
    
    # Apply filters
    if department_filter:
        reports = reports.filter(attachment__student__department_id=department_filter)
    
    if date_filter == 'week':
        reports = reports.filter(uploaded_at__gte=timezone.now() - timedelta(days=7))
    elif date_filter == 'month':
        reports = reports.filter(uploaded_at__gte=timezone.now() - timedelta(days=30))
    
    # Pagination
    paginator = Paginator(reports, 25)  # Show 25 reports per page
    try:
        reports_page = paginator.page(page)
    except PageNotAnInteger:
        reports_page = paginator.page(1)
    except EmptyPage:
        reports_page = paginator.page(paginator.num_pages)
    
    # Statistics
    total_reports = ReportUpload.objects.count()
    reports_this_week = ReportUpload.objects.filter(
        uploaded_at__gte=timezone.now() - timedelta(days=7)
    ).count()
    reports_this_month = ReportUpload.objects.filter(
        uploaded_at__gte=timezone.now() - timedelta(days=30)
    ).count()
    
    departments = Department.objects.all()
    
    context = {
        'reports': reports_page,
        'total_reports': total_reports,
        'reports_this_week': reports_this_week,
        'reports_this_month': reports_this_month,
        'departments': departments,
        'selected_department': department_filter,
        'selected_date_range': date_filter,
    }
    return render(request, 'attachments/reports_dashboard.html', context)

@user_passes_test(is_admin)
def workload_overview(request):
    """Lecturer workload analysis"""
    lecturers = Lecturer.objects.filter(is_active=True).annotate(
        assigned_count=Count('assigned_students'),
        available_slots=models.F('max_students') - Count('assigned_students'),
        workload_percentage=(Count('assigned_students') * 100.0 / models.F('max_students'))
    ).order_by('-workload_percentage')
    
    # Statistics
    total_lecturers = lecturers.count()
    overloaded_lecturers = lecturers.filter(workload_percentage__gt=100).count()
    optimal_lecturers = lecturers.filter(workload_percentage__gte=70, workload_percentage__lte=100).count()
    underutilized_lecturers = lecturers.filter(workload_percentage__lt=70).count()
    
    context = {
        'lecturers': lecturers,
        'total_lecturers': total_lecturers,
        'overloaded_lecturers': overloaded_lecturers,
        'optimal_lecturers': optimal_lecturers,
        'underutilized_lecturers': underutilized_lecturers,
    }
    return render(request, 'attachments/workload_overview.html', context)

@user_passes_test(is_admin)
def export_data(request):
    """Data export functionality"""
    format_type = request.GET.get('format', 'excel')
    data_type = request.GET.get('type', 'students')
    
    if data_type == 'students':
        return export_students_data(request, format_type)
    elif data_type == 'placements':
        return export_placements_data(request, format_type)
    elif data_type == 'reports':
        return export_reports_data(request, format_type)
    else:
        messages.error(request, 'Invalid export type')
        return redirect('attachments:admin_dashboard')

def export_students_data(request, format_type):
    """Export students data"""
    students = User.objects.filter(user_type=1).select_related('department', 'course')
    
    if format_type == 'excel':
        response = HttpResponse(content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename="students_export.xlsx"'
        
        # Simple CSV export for now
        writer = csv.writer(response)
        writer.writerow(['Student ID', 'Full Name', 'Email', 'Department', 'Course', 'Year of Study', 'Registration Date'])
        
        for student in students:
            writer.writerow([
                student.student_id,
                student.get_full_name(),
                student.email,
                student.department.name if student.department else '',
                student.course.name if student.course else '',
                student.year_of_study,
                student.date_joined.strftime('%Y-%m-%d')
            ])
        
        return response
    
    elif format_type == 'pdf':
        # PDF export
        html_string = render_to_string('attachments/export/students_pdf.html', {
            'students': students,
            'export_date': timezone.now()
        })
        
        html = HTML(string=html_string)
        pdf_file = html.write_pdf()
        
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="students_export.pdf"'
        return response
    
    else:
        messages.error(request, 'Unsupported export format')
        return redirect('attachments:admin_dashboard')

def export_placements_data(request, format_type):
    """Export placements data"""
    placements = PlacementFormSubmission.objects.select_related('student', 'department')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="placements_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Student', 'Department', 'Firm', 'Supervisor', 'Start Date', 'End Date', 'Status'])
    
    for placement in placements:
        writer.writerow([
            placement.student.get_full_name(),
            placement.department.name,
            placement.firm_name,
            placement.supervisor_name,
            placement.start_date,
            placement.end_date,
            placement.status
        ])
    
    return response

def export_reports_data(request, format_type):
    """Export reports data"""
    reports = ReportUpload.objects.select_related('attachment', 'attachment__student')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="reports_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Student', 'Attachment', 'File Name', 'Uploaded At'])
    
    for report in reports:
        writer.writerow([
            report.attachment.student.get_full_name(),
            report.attachment.organization,
            report.file.name,
            report.uploaded_at
        ])
    
    return response

def communication(request):
    """Industrial Attachment Placement Form with enhanced view"""
    # Get user's attachments (for sidebar)
    attachments = Attachment.objects.filter(student=request.user)
    current_attachment = attachments.first()
    
    # Check if user already submitted placement form for current cycle
    current_year = timezone.now().year
    existing_submission = PlacementFormSubmission.objects.filter(
        student=request.user,
        start_date__year=current_year
    ).first()
    
    # Get all placement forms for admin view
    all_placements = None
    if request.user.is_staff or getattr(request.user, 'user_type', None) == 4:  # Admin
        all_placements = PlacementFormSubmission.objects.select_related(
            'student', 'department', 'student__course'
        ).order_by('-submitted_at')
    
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
                off_days=request.POST.getlist('off_days')
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
        'all_placements': all_placements,
        'current_year': current_year,
    }
    
    return render(request, 'attachments/communication.html', context)
    
    # Get counts for the template
    total_students = User.objects.filter(user_type=1).count()
    unassigned_students = User.objects.filter(user_type=1, student_assignments__isnull=True).count()
    total_lecturers = Lecturer.objects.filter(is_active=True).count()
    
    context = {
        'total_students': total_students,
        'unassigned_students': unassigned_students,
        'total_lecturers': total_lecturers,
    }
    return render(request, 'attachments/communication_center.html', context)

@user_passes_test(is_admin)
def student_registration(request):
    """Manual student registration by admin"""
    departments = Department.objects.all()
    
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        student_id = request.POST.get('student_id', '').strip()
        year_of_study = request.POST.get('year_of_study')
        department_id = request.POST.get('department')
        course_id = request.POST.get('course')
        
        # Basic validation
        if not all([first_name, last_name, email, student_id, year_of_study, department_id, course_id]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('attachments:student_registration')
        
        try:
            # Check if email already exists
            if User.objects.filter(email=email).exists():
                messages.error(request, 'A user with this email already exists.')
                return redirect('attachments:student_registration')
            
            # Check if student ID already exists
            if User.objects.filter(student_id=student_id).exists():
                messages.error(request, 'A student with this ID already exists.')
                return redirect('attachments:student_registration')
            
            # Generate secure random password
            password = generate_secure_password()
            
            # Create user
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                user_type=1,  # Student type
                student_id=student_id,
                year_of_study=year_of_study,
                department_id=department_id,
                course_id=course_id
            )
            
            messages.success(request, 
                f'Student {first_name} {last_name} created successfully! '
                f'Login credentials:<br>'
                f'Student ID: <strong>{student_id}</strong><br>'
                f'Password: <strong>{password}</strong>'
            )
            
            return redirect('attachments:student_registration')
                
        except Exception as e:
            messages.error(request, f'Error creating student: {str(e)}')
    
    context = {
        'departments': departments,
    }
    
    return render(request, 'attachments/student_registration.html', context)

@user_passes_test(is_admin)
def auto_assign_students(request):
    """Automatically assign unassigned students to available lecturers"""
    try:
        # Get all unassigned students for current academic year
        current_year = timezone.now().year
        unassigned_students = User.objects.filter(
            user_type=1,
            student_assignments__isnull=True
        ).select_related('department', 'course')
        
        # Get all active lecturers with available slots, ordered by current workload
        available_lecturers = Lecturer.objects.filter(
            is_active=True
        ).annotate(
            assigned_count=Count('assigned_students'),
            available_slots=models.F('max_students') - Count('assigned_students')
        ).filter(available_slots__gt=0).select_related('user', 'department')
        
        assignments_made = 0
        errors = []
        
        # Group students by department for efficient assignment
        students_by_department = {}
        for student in unassigned_students:
            dept_id = student.department.id if student.department else 0
            if dept_id not in students_by_department:
                students_by_department[dept_id] = []
            students_by_department[dept_id].append(student)
        
        # Group lecturers by department
        lecturers_by_department = {}
        for lecturer in available_lecturers:
            dept_id = lecturer.department.id
            if dept_id not in lecturers_by_department:
                lecturers_by_department[dept_id] = []
            lecturers_by_department[dept_id].append(lecturer)
        
        # Assign students department-wise
        for dept_id, students in students_by_department.items():
            if dept_id in lecturers_by_department and lecturers_by_department[dept_id]:
                lecturers = lecturers_by_department[dept_id]
                
                # Sort lecturers by current workload (least assigned first)
                lecturers_sorted = sorted(lecturers, key=lambda x: x.assigned_count)
                
                # Round-robin assignment to distribute students evenly
                for i, student in enumerate(students):
                    lecturer = lecturers_sorted[i % len(lecturers_sorted)]
                    
                    # Check if lecturer still has available slots
                    if lecturer.assigned_count < lecturer.max_students:
                        try:
                            # Get student's placement form if exists
                            placement_form = PlacementFormSubmission.objects.filter(
                                student=student
                            ).first()
                            
                            # Create assignment
                            assignment = StudentAssignment(
                                student=student,
                                lecturer=lecturer,
                                placement_form=placement_form,
                                academic_year=current_year
                            )
                            assignment.save()
                            
                            # Update lecturer's assigned count
                            lecturer.assigned_count += 1
                            assignments_made += 1
                            
                        except Exception as e:
                            errors.append(f"Failed to assign {student.get_full_name()}: {str(e)}")
                    else:
                        errors.append(f"Lecturer {lecturer.user.get_full_name()} has no available slots for {student.get_full_name()}")
            else:
                # No lecturers in this department, try to find any available lecturer
                if available_lecturers:
                    lecturers_sorted = sorted(available_lecturers, key=lambda x: x.assigned_count)
                    for student in students:
                        assigned = False
                        for lecturer in lecturers_sorted:
                            if lecturer.assigned_count < lecturer.max_students:
                                try:
                                    placement_form = PlacementFormSubmission.objects.filter(
                                        student=student
                                    ).first()
                                    
                                    assignment = StudentAssignment(
                                        student=student,
                                        lecturer=lecturer,
                                        placement_form=placement_form,
                                        academic_year=current_year
                                    )
                                    assignment.save()
                                    
                                    lecturer.assigned_count += 1
                                    assignments_made += 1
                                    assigned = True
                                    break
                                    
                                except Exception as e:
                                    errors.append(f"Failed to assign {student.get_full_name()}: {str(e)}")
                        
                        if not assigned:
                            errors.append(f"No available lecturer for {student.get_full_name()} (Department: {student.department.name if student.department else 'None'})")
        
        if assignments_made > 0:
            messages.success(request, f'Successfully auto-assigned {assignments_made} students to lecturers!')
        
        if errors:
            messages.warning(request, f'Some assignments failed: {", ".join(errors[:5])}' + ("..." if len(errors) > 5 else ""))
        
        if assignments_made == 0 and not errors:
            messages.info(request, 'No students available for auto-assignment or no lecturers with available slots.')
            
    except Exception as e:
        messages.error(request, f'Error during auto-assignment: {str(e)}')
    
    return redirect('attachments:assignment_dashboard')

@user_passes_test(is_admin)
def smart_assign_department(request, department_id):
    """Smart assignment for a specific department"""
    try:
        department = get_object_or_404(Department, id=department_id)
        current_year = timezone.now().year
        
        # Get unassigned students in this department
        unassigned_students = User.objects.filter(
            user_type=1,
            department=department,
            student_assignments__isnull=True
        ).select_related('course')
        
        # Get available lecturers in this department
        available_lecturers = Lecturer.objects.filter(
            department=department,
            is_active=True
        ).annotate(
            assigned_count=Count('assigned_students'),
            available_slots=models.F('max_students') - Count('assigned_students')
        ).filter(available_slots__gt=0).select_related('user')
        
        if not available_lecturers:
            messages.error(request, f'No available lecturers in {department.name} department.')
            return redirect('attachments:department_placements', department_id=department_id)
        
        if not unassigned_students:
            messages.info(request, f'No unassigned students in {department.name} department.')
            return redirect('attachments:department_placements', department_id=department_id)
        
        assignments_made = 0
        
        # Sort lecturers by workload (least assigned first)
        lecturers_sorted = sorted(available_lecturers, key=lambda x: x.assigned_count)
        
        # Round-robin assignment
        for i, student in enumerate(unassigned_students):
            lecturer = lecturers_sorted[i % len(lecturers_sorted)]
            
            if lecturer.assigned_count < lecturer.max_students:
                try:
                    placement_form = PlacementFormSubmission.objects.filter(
                        student=student
                    ).first()
                    
                    assignment = StudentAssignment(
                        student=student,
                        lecturer=lecturer,
                        placement_form=placement_form,
                        academic_year=current_year
                    )
                    assignment.save()
                    
                    lecturer.assigned_count += 1
                    assignments_made += 1
                    
                except Exception as e:
                    messages.error(request, f"Failed to assign {student.get_full_name()}: {str(e)}")
        
        if assignments_made > 0:
            messages.success(request, f'Successfully assigned {assignments_made} students in {department.name} department!')
        else:
            messages.info(request, f'No assignments made in {department.name} department.')
            
    except Exception as e:
        messages.error(request, f'Error during department assignment: {str(e)}')
    
    return redirect('attachments:department_placements', department_id=department_id)