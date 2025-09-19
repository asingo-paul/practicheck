# attachments/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Sum
from .models import Attachment, LogbookEntry, Industry, ReportUpload
from .forms import AttachmentForm, LogbookEntryForm
import os
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required, user_passes_test
# from .models import Report, Attachment
# from .forms import ReportForm


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

    # Check how many reports exist
    reports = attachment.reports.all()
    if request.method == "POST":
        if reports.count() >= 2:
            messages.error(request, "You can only upload a maximum of 2 reports.")
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