from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Attachment, LogbookEntry, Report
from .forms import LogbookEntryForm, ReportForm
from django.http import HttpResponse
from django.utils import timezone
from datetime import timedelta
from accounts.decorators import role_required
from django.db.models import Sum

# # attachments/views.py
# @login_required
# def dashboard(request):
#     user = request.user
#     context = {}
    
#     if user.user_type == 1:  # Student
#         attachments = Attachment.objects.filter(student=user)
#         current_attachment = attachments.first() if attachments else None
#         context['attachments'] = attachments
#         context['current_attachment'] = current_attachment
        
#         # Get logbook stats
#         if current_attachment:
#             entries = LogbookEntry.objects.filter(attachment=current_attachment)
#             context['logbook_entries_count'] = entries.count()
#             context['total_hours'] = entries.aggregate(Sum('hours_worked'))['hours_worked__sum'] or 0
        
#         template = 'attachments/dashboard.html'
        
#     elif user.user_type == 2:  # Supervisor
#         # Redirect to supervisor dashboard
#         return redirect('evaluations:supervisor_dashboard')
        
#     elif user.user_type == 3:  # Lecturer
#         # Redirect to lecturer dashboard
#         return redirect('evaluations:lecturer_dashboard')
    
#     return render(request, template, context)

@login_required
@role_required([1]) # Only students
def dashboard(request):
    user = request.user
    attachments = Attachment.objects.filter(student=user)
    current_attachment = attachments.first() if attachments else None

    # If student has no attachments, redirect to welcome page
    if not attachments.exists():
        return redirect('attachments:welcome')
    
    current_attachment = attachments.first()
    
    context = {
        'attachments': attachments,
        'current_attachment': current_attachment,
    }
    
    if current_attachment:
        # Calculate attachment progress
        today = timezone.now().date()
        start_date = current_attachment.start_date
        end_date = current_attachment.end_date
        
        total_days = (end_date - start_date).days
        days_completed = (today - start_date).days
        days_remaining = (end_date - today).days
        
        # Ensure we don't have negative days
        days_completed = max(0, min(days_completed, total_days))
        days_remaining = max(0, days_remaining)
        
        completion_percentage = int((days_completed / total_days) * 100) if total_days > 0 else 0
        
        # Get logbook stats
        entries = LogbookEntry.objects.filter(attachment=current_attachment)
        logbook_entries_count = entries.count()
        total_hours = entries.aggregate(Sum('hours_worked'))['hours_worked__sum'] or 0
        
        # Get supervisor rating if available
        supervisor_rating = None
        try:
            if current_attachment.supervisor_evaluation:
                # Convert 100-point scale to 5-point scale for display
                supervisor_rating = round((current_attachment.supervisor_evaluation.overall_score / 100) * 5, 1)
        except:
            pass
        
        # Recent activities (simplified for example)
        recent_activities = [
            {
                'title': 'Logbook Entry Submitted',
                'description': 'Added entry for today\'s tasks',
                'date': 'Today, 10:30 AM',
                'type': 'logbook'
            },
            {
                'title': 'Weekly Report Uploaded',
                'description': 'Submitted weekly progress report',
                'date': 'Yesterday, 3:45 PM',
                'type': 'report'
            },
            {
                'title': 'Supervisor Feedback',
                'description': 'Received comments on latest submission',
                'date': 'Oct 15, 2:30 PM',
                'type': 'feedback'
            }
        ]
        
        # Upcoming tasks
        upcoming_tasks = [
            {
                'title': 'Weekly Logbook Submission',
                'due_date': 'Tomorrow',
                'priority': 'primary'
            },
            {
                'title': 'Project Milestone Review',
                'due_date': '3 days',
                'priority': 'info'
            },
            {
                'title': 'Mid-Attachment Evaluation',
                'due_date': '1 week',
                'priority': 'warning'
            }
        ]
        
        context.update({
            'logbook_entries_count': logbook_entries_count,
            'total_hours': total_hours,
            'completion_percentage': completion_percentage,
            'supervisor_rating': supervisor_rating,
            'days_completed': days_completed,
            'days_remaining': days_remaining,
            'total_days': total_days,
            'recent_activities': recent_activities,
            'upcoming_tasks': upcoming_tasks,
        })
    
    return render(request, 'attachments/dashboard.html', context)

@login_required
def logbook(request, attachment_id=None):
    if request.user.user_type != 1:  # Only students can access logbook
        messages.error(request, "You don't have permission to access this page.")
        return redirect('attachments:dashboard')
    
    attachment = get_object_or_404(Attachment, id=attachment_id, student=request.user)
    
    if request.method == 'POST':
        form = LogbookEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.attachment = attachment
            entry.save()
            messages.success(request, 'Logbook entry added successfully!')
            return redirect('attachments:logbook', attachment_id=attachment.id)
    else:
        form = LogbookEntryForm()
    
    entries = LogbookEntry.objects.filter(attachment=attachment)
    
    return render(request, 'attachments/logbook.html', {
        'attachment': attachment,
        'form': form,
        'entries': entries
    })

@login_required
def report_upload(request, attachment_id=None):
    if request.user.user_type != 1:  # Only students can upload reports
        messages.error(request, "You don't have permission to access this page.")
        return redirect('attachments:dashboard')
    
    attachment = get_object_or_404(Attachment, id=attachment_id, student=request.user)
    
    try:
        report = Report.objects.get(attachment=attachment)
    except Report.DoesNotExist:
        report = None
    
    if request.method == 'POST':
        if report:
            form = ReportForm(request.POST, request.FILES, instance=report)
        else:
            form = ReportForm(request.POST, request.FILES)
        
        if form.is_valid():
            report = form.save(commit=False)
            report.attachment = attachment
            report.save()
            messages.success(request, 'Report uploaded successfully!')
            return redirect('attachments:report_upload', attachment_id=attachment.id)
    else:
        if report:
            form = ReportForm(instance=report)
        else:
            form = ReportForm()
    
    return render(request, 'attachments/report_upload.html', {
        'attachment': attachment,
        'form': form,
        'report': report
    })

@login_required
def assessment(request):
    # This would show assessment status and results
    return render(request, 'attachments/assessment.html')

@login_required
def communication(request):
    # This would handle communication between students, supervisors, and lecturers
    return render(request, 'attachments/communication.html')



# def logbook_list(request):
#     return HttpResponse("This is the Logbook List page.")


def index(request):
    return HttpResponse("Welcome to Attachments App")

# def dashboard(request):
#     return render(request, "dashboard.html")

# attachments/views.py
@login_required
@role_required([1])  # Only students
def welcome(request):
    """Welcome page for students without attachments"""
    return render(request, 'attachments/welcome.html')
