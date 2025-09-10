from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from attachments.models import Attachment
from .models import EvaluationCriteria, SupervisorEvaluation, LecturerEvaluation, FinalAssessment
from .forms import SupervisorEvaluationForm, LecturerEvaluationForm
from accounts.decorators import role_required


def index(request):
    return HttpResponse("Hello from Evaluations app!")


@login_required
@role_required([2])  # Only supervisors
def supervisor_dashboard(request):
    supervised_attachments = Attachment.objects.filter(supervisor=request.user)
    evaluations = SupervisorEvaluation.objects.filter(supervisor=request.user)
    
    # Calculate pending evaluations
    pending_evaluations = supervised_attachments.count() - evaluations.count()
    
    return render(request, 'evaluations/supervisor_dashboard.html', {
        'supervised_attachments': supervised_attachments,
        'evaluations': evaluations,
        'pending_evaluations': pending_evaluations
    })


@login_required
@role_required([2])  # Only supervisors
def evaluation_form(request, attachment_id):
    attachment = get_object_or_404(Attachment, id=attachment_id, supervisor=request.user)
    criteria_list = EvaluationCriteria.objects.all()
    
    if request.method == 'POST':
        form = SupervisorEvaluationForm(request.POST, criteria_list=criteria_list)
        if form.is_valid():
            # Calculate overall score
            criteria_scores = {}
            total_score = 0
            total_weight = 0
            
            for criteria in criteria_list:
                score = form.cleaned_data[f'criteria_{criteria.id}']
                criteria_scores[criteria.id] = float(score)
                total_score += float(score) * float(criteria.weight)
                total_weight += float(criteria.weight)
            
            overall_score = total_score / total_weight if total_weight > 0 else 0
            
            # Create or update evaluation
            evaluation, created = SupervisorEvaluation.objects.update_or_create(
                attachment=attachment,
                supervisor=request.user,
                defaults={
                    'criteria_scores': criteria_scores,
                    'overall_score': overall_score,
                    'comments': form.cleaned_data['comments']
                }
            )
            
            messages.success(request, 'Evaluation submitted successfully!')
            return redirect('evaluations:supervisor_dashboard')
    else:
        # Try to get existing evaluation for this attachment
        try:
            existing_evaluation = SupervisorEvaluation.objects.get(
                attachment=attachment, 
                supervisor=request.user
            )
            form = SupervisorEvaluationForm(
                criteria_list=criteria_list, 
                initial={
                    'comments': existing_evaluation.comments
                }
            )
        except SupervisorEvaluation.DoesNotExist:
            form = SupervisorEvaluationForm(criteria_list=criteria_list)
    
    return render(request, 'evaluations/evaluation_form.html', {
        'attachment': attachment,
        'form': form,
        'criteria_list': criteria_list
    })


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


@login_required
@role_required([3])  # Only lecturers
def grading_panel(request, attachment_id):
    attachment = get_object_or_404(Attachment, id=attachment_id)
    criteria_list = EvaluationCriteria.objects.all()
    
    # Check if supervisor evaluation exists
    try:
        supervisor_evaluation = SupervisorEvaluation.objects.get(attachment=attachment)
    except SupervisorEvaluation.DoesNotExist:
        supervisor_evaluation = None
    
    if request.method == 'POST':
        form = LecturerEvaluationForm(request.POST, criteria_list=criteria_list)
        if form.is_valid():
            # Calculate overall score
            criteria_scores = {}
            total_score = 0
            total_weight = 0
            
            for criteria in criteria_list:
                score = form.cleaned_data[f'criteria_{criteria.id}']
                criteria_scores[criteria.id] = float(score)
                total_score += float(score) * float(criteria.weight)
                total_weight += float(criteria.weight)
            
            overall_score = total_score / total_weight if total_weight > 0 else 0
            
            # Create or update evaluation
            evaluation, created = LecturerEvaluation.objects.update_or_create(
                attachment=attachment,
                lecturer=request.user,
                defaults={
                    'criteria_scores': criteria_scores,
                    'overall_score': overall_score,
                    'comments': form.cleaned_data['comments']
                }
            )
            
            # Create or update final assessment if supervisor evaluation exists
            if supervisor_evaluation:
                final_score = (supervisor_evaluation.overall_score + overall_score) / 2
                
                # Determine grade
                if final_score >= 90:
                    grade = 'A'
                elif final_score >= 80:
                    grade = 'B'
                elif final_score >= 70:
                    grade = 'C'
                elif final_score >= 60:
                    grade = 'D'
                else:
                    grade = 'F'
                
                FinalAssessment.objects.update_or_create(
                    attachment=attachment,
                    defaults={
                        'supervisor_score': supervisor_evaluation.overall_score,
                        'lecturer_score': overall_score,
                        'final_score': final_score,
                        'grade': grade,
                        'assessed_by': request.user
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
            form = LecturerEvaluationForm(
                criteria_list=criteria_list, 
                initial={
                    'comments': existing_evaluation.comments
                }
            )
        except LecturerEvaluation.DoesNotExist:
            form = LecturerEvaluationForm(criteria_list=criteria_list)
    
    return render(request, 'evaluations/grading_panel.html', {
        'attachment': attachment,
        'form': form,
        'criteria_list': criteria_list,
        'supervisor_evaluation': supervisor_evaluation
    })


