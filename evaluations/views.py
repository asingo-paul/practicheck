from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from attachments.models import Attachment
from .models import EvaluationCriteria, SupervisorEvaluation, LecturerEvaluation, FinalAssessment
from .forms import SupervisorEvaluationForm, LecturerEvaluationForm
from accounts.decorators import role_required, supervisor_required
from django.db.models import Sum


def index(request):
    return HttpResponse("Hello from Evaluations app!")


@login_required
@role_required([2])  # Only supervisors
def supervisor_dashboard(request):
    supervised_attachments = Attachment.objects.filter(supervisor_email=request.user.email)
    evaluations = SupervisorEvaluation.objects.filter(supervisor=request.user)
    
    # Calculate pending evaluations
    pending_evaluations = supervised_attachments.count() - evaluations.count()
    
    return render(request, 'evaluations/supervisor_dashboard.html', {
        'supervised_attachments': supervised_attachments,
        'evaluations': evaluations,
        'pending_evaluations': pending_evaluations
    })


# @login_required
# @role_required([2])  # Only supervisors
# def evaluation_form(request, attachment_id):
#      # Filter by supervisor email
#     attachment = get_object_or_404(Attachment, id=attachment_id, supervisor_email=request.user.email)
#     criteria_list = EvaluationCriteria.objects.all()
    
#     if request.method == 'POST':
#         form = SupervisorEvaluationForm(request.POST, criteria_list=criteria_list)
#         if form.is_valid():
#             # Calculate overall score
#             criteria_scores = {}
#             total_score = 0
#             total_weight = 0
            
#             for criteria in criteria_list:
#                 score = form.cleaned_data[f'criteria_{criteria.id}']
#                 criteria_scores[criteria.id] = float(score)
#                 total_score += float(score) * float(criteria.weight)
#                 total_weight += float(criteria.weight)
            
#             overall_score = total_score / total_weight if total_weight > 0 else 0
            
#             # Create or update evaluation
#             evaluation, created = SupervisorEvaluation.objects.update_or_create(
#                 attachment=attachment,
#                 supervisor=request.user,
#                 defaults={
#                     'criteria_scores': criteria_scores,
#                     'overall_score': overall_score,
#                     'comments': form.cleaned_data['comments']
#                 }
#             )
            
#             messages.success(request, 'Evaluation submitted successfully!')
#             return redirect('evaluations:supervisor_dashboard')
#     else:
#         # Try to get existing evaluation for this attachment
#         try:
#             existing_evaluation = SupervisorEvaluation.objects.get(
#                 attachment=attachment, 
#                 supervisor=request.user
#             )
#             form = SupervisorEvaluationForm(
#                 criteria_list=criteria_list, 
#                 initial={
#                     'comments': existing_evaluation.comments
#                 }
#             )
#         except SupervisorEvaluation.DoesNotExist:
#             form = SupervisorEvaluationForm(criteria_list=criteria_list)
    
#     return render(request, 'evaluations/evaluation_form.html', {
#         'attachment': attachment,
#         'form': form,
#         'criteria_list': criteria_list
#     })


# evaluations/views.py
@login_required
@supervisor_required
def evaluation_form(request, attachment_id):
    attachment = get_object_or_404(Attachment, id=attachment_id)
    
    # Verify this supervisor is assigned to this attachment
    if request.user != attachment.supervisor:
        messages.error(request, "You are not assigned as supervisor for this attachment.")
        return redirect('evaluations:supervisor_dashboard')
    
    # Get evaluation criteria
    criteria_list = EvaluationCriteria.objects.all()
    
    try:
        existing_evaluation = SupervisorEvaluation.objects.get(
            attachment=attachment,
            supervisor=request.user
        )
        is_edit = True
    except SupervisorEvaluation.DoesNotExist:
        existing_evaluation = None
        is_edit = False
    
    if request.method == 'POST':
        form = SupervisorEvaluationForm(
            request.POST, 
            instance=existing_evaluation,
            criteria_list=criteria_list  # This requires the custom __init__ method
        )
        
        if form.is_valid():
            evaluation = form.save(commit=False)
            evaluation.attachment = attachment
            evaluation.supervisor = request.user
            
            # Handle criteria scores
            criteria_scores = {}
            for criteria in criteria_list:
                field_name = f'criteria_{criteria.id}'
                criteria_scores[criteria.id] = int(form.cleaned_data.get(field_name, 3))
            
            evaluation.criteria_scores = criteria_scores
            evaluation.save()
            
            messages.success(request, 'Evaluation submitted successfully!')
            return redirect('evaluations:supervisor_dashboard')
    else:
        form = SupervisorEvaluationForm(
            instance=existing_evaluation,
            criteria_list=criteria_list  # This requires the custom __init__ method
        )
    
    context = {
        'form': form,
        'attachment': attachment,
        'criteria_list': criteria_list,
        'is_edit': is_edit,
    }
    
    return render(request, 'evaluations/evaluation_form.html', context)

@login_required
@role_required([3])  # Only lecturers
def lecturer_dashboard(request):
    # Get all attachments (or those assigned to this lecturer)
    all_attachments = Attachment.objects.all()
    evaluations = LecturerEvaluation.objects.filter(lecturer=request.user)
    
    # Calculate pending evaluations
    completed_attachments = [eval.attachment for eval in evaluations]
    pending_evaluations = all_attachments.count() - len(completed_attachments)
    
    return render(request, 'evaluations/lecturer_dashboard.html', {
        'all_attachments': all_attachments,
        'evaluations': evaluations,
        'pending_evaluations': pending_evaluations
    })


# @login_required
# @role_required([3])  # Only lecturers
# def grading_panel(request, attachment_id):
#     attachment = get_object_or_404(Attachment, id=attachment_id)
#     criteria_list = EvaluationCriteria.objects.all()
    
#     # Check if supervisor evaluation exists
#     try:
#         supervisor_evaluation = SupervisorEvaluation.objects.get(attachment=attachment)
#     except SupervisorEvaluation.DoesNotExist:
#         supervisor_evaluation = None
    
#     if request.method == 'POST':
#         form = LecturerEvaluationForm(request.POST, criteria_list=criteria_list)
#         if form.is_valid():
#             # Calculate overall score
#             criteria_scores = {}
#             total_score = 0
#             total_weight = 0
            
#             for criteria in criteria_list:
#                 score = form.cleaned_data[f'criteria_{criteria.id}']
#                 criteria_scores[criteria.id] = float(score)
#                 total_score += float(score) * float(criteria.weight)
#                 total_weight += float(criteria.weight)
            
#             overall_score = total_score / total_weight if total_weight > 0 else 0
            
#             # Create or update evaluation
#             evaluation, created = LecturerEvaluation.objects.update_or_create(
#                 attachment=attachment,
#                 lecturer=request.user,
#                 defaults={
#                     'criteria_scores': criteria_scores,
#                     'overall_score': overall_score,
#                     'comments': form.cleaned_data['comments']
#                 }
#             )
            
#             # Create or update final assessment if supervisor evaluation exists
#             if supervisor_evaluation:
#                 final_score = (supervisor_evaluation.overall_score + overall_score) / 2
                
#                 # Determine grade
#                 if final_score >= 90:
#                     grade = 'A'
#                 elif final_score >= 80:
#                     grade = 'B'
#                 elif final_score >= 70:
#                     grade = 'C'
#                 elif final_score >= 60:
#                     grade = 'D'
#                 else:
#                     grade = 'F'
                
#                 FinalAssessment.objects.update_or_create(
#                     attachment=attachment,
#                     defaults={
#                         'supervisor_score': supervisor_evaluation.overall_score,
#                         'lecturer_score': overall_score,
#                         'final_score': final_score,
#                         'grade': grade,
#                         'assessed_by': request.user
#                     }
#                 )
            
#             messages.success(request, 'Evaluation submitted successfully!')
#             return redirect('evaluations:lecturer_dashboard')
#     else:
#         # Try to get existing evaluation for this attachment
#         try:
#             existing_evaluation = LecturerEvaluation.objects.get(
#                 attachment=attachment, 
#                 lecturer=request.user
#             )
#             form = LecturerEvaluationForm(
#                 criteria_list=criteria_list, 
#                 initial={
#                     'comments': existing_evaluation.comments
#                 }
#             )
#         except LecturerEvaluation.DoesNotExist:
#             form = LecturerEvaluationForm(criteria_list=criteria_list)
    
#     return render(request, 'evaluations/grading_panel.html', {
#         'attachment': attachment,
#         'form': form,
#         'criteria_list': criteria_list,
#         'supervisor_evaluation': supervisor_evaluation
#     })


# evaluations/views.py
@login_required
@role_required([2])  # Only supervisors
def view_student_logbook(request, attachment_id):
    attachment = get_object_or_404(Attachment, id=attachment_id)
    
    # Verify this supervisor is associated with the attachment
    if attachment.supervisor_email != request.user.email:
        messages.error(request, "You don't have permission to view this student's logbook.")
        return redirect('evaluations:supervisor_dashboard')
    
    entries = LogbookEntry.objects.filter(attachment=attachment).order_by('-entry_date')
    
    return render(request, 'evaluations/student_logbook.html', {
        'attachment': attachment,
        'entries': entries,
        'student': attachment.student
    })

@login_required
@role_required([3])  # Only lecturers
def grading_panel(request, attachment_id):
    attachment = get_object_or_404(Attachment, id=attachment_id)
    
    # Check if supervisor evaluation exists
    try:
        supervisor_evaluation = SupervisorEvaluation.objects.get(attachment=attachment)
    except SupervisorEvaluation.DoesNotExist:
        supervisor_evaluation = None
    
    if request.method == 'POST':
        form = LecturerEvaluationForm(request.POST)
        if form.is_valid():
            # Create or update evaluation
            evaluation, created = LecturerEvaluation.objects.update_or_create(
                attachment=attachment,
                lecturer=request.user,
                defaults={
                    'comments': form.cleaned_data['comments'],
                    'grade': form.cleaned_data['grade']
                }
            )
            
            messages.success(request, 'Evaluation submitted successfully!')
            return redirect('evaluations:lecturer_dashboard')
    else:
        # Try to get existing evaluation for this attachment
        try:
            existing_evaluation = LecturerEvaluation.objects.get(
                attachment=attachment, 
                lecturer=request.user
            )
            form = LecturerEvaluationForm(instance=existing_evaluation)
        except LecturerEvaluation.DoesNotExist:
            form = LecturerEvaluationForm()
    
    return render(request, 'evaluations/grading_panel.html', {
        'attachment': attachment,
        'form': form,
        'supervisor_evaluation': supervisor_evaluation
    })