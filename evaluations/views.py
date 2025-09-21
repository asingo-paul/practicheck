from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from attachments.models import Attachment, LogbookEntry
from .models import (
    EvaluationCriteria,
    SupervisorEvaluation,
    LecturerEvaluation,
    FinalAssessment,
    LogbookEvaluation,
)
from .forms import SupervisorEvaluationForm, LecturerEvaluationForm
from accounts.decorators import role_required, supervisor_required
from django.db.models import Avg


# def index(request):
#     return HttpResponse("Hello from Evaluations app!")


# ---------------- Supervisor Views ---------------- #
@login_required
@role_required([2])  # Supervisors only
def supervisor_dashboard(request):
    """Show supervisor dashboard with students under supervision."""
    supervised_attachments = Attachment.objects.filter(supervisor_email=request.user.email)
    evaluations = SupervisorEvaluation.objects.filter(supervisor=request.user)

    # Calculate pending evaluations
    pending_evaluations = supervised_attachments.count() - evaluations.count()

    # Calculate average rating (assuming overall_score is 0-100 scale)
    avg_score = evaluations.aggregate(avg_score=Avg('overall_rating'))['avg_score'] or 0

    # Convert 0-100 to 0-5 scale and format
    average_rating = f"{(avg_score/20):.1f}/5"

    return render(request, "evaluations/supervisor_dashboard.html", {
        "supervised_attachments": supervised_attachments,
        "evaluations": evaluations,
        "pending_evaluations": pending_evaluations,
        "average_rating": average_rating,  # pass to template
    })


@login_required
@supervisor_required
def student_logbooks(request, attachment_id):
    """Supervisor views all logbooks of a student."""
    attachment = get_object_or_404(Attachment, id=attachment_id)

    if request.user.email != attachment.supervisor_email:
        messages.error(request, "You are not assigned as supervisor for this student.")
        return redirect("evaluations:supervisor_dashboard")

    logbooks = LogbookEntry.objects.filter(attachment=attachment).order_by("-entry_date")

    return render(request, "attachments/logbook.html", {
        "attachment": attachment,
        "logbooks": logbooks,
        "mode": "supervisor",  # tells template to show evaluation actions
    })


@login_required
@supervisor_required
def evaluate_logbook(request, logbook_id):
    """Supervisor evaluates a single logbook entry."""
    logbook_entry = get_object_or_404(LogbookEntry, id=logbook_id)
    attachment = logbook_entry.attachment

    if request.user.email != attachment.supervisor_email:
        messages.error(request, "You are not assigned as supervisor for this student.")
        return redirect("evaluations:supervisor_dashboard")

    evaluation = getattr(logbook_entry, "evaluation", None)

    if request.method == "POST":
        score = request.POST.get("score")
        comments = request.POST.get("comments")

        if evaluation:
            evaluation.score = score
            evaluation.comments = comments
            evaluation.save()
            messages.success(request, "Logbook evaluation updated.")
        else:
            LogbookEvaluation.objects.create(
                logbook_entry=logbook_entry,
                supervisor=request.user,
                score=score,
                comments=comments,
            )
            messages.success(request, "Logbook evaluated successfully.")

        return redirect("evaluations:student_logbooks", attachment.id)

    return render(request, "evaluations/evaluate_logbook.html", {
        "logbook_entry": logbook_entry,
        "evaluation": evaluation,
    })

@login_required
@supervisor_required
def evaluation_form(request, attachment_id):
    """Supervisor evaluates student overall (criteria-based)."""
    attachment = get_object_or_404(Attachment, id=attachment_id)

    # ✅ Authorization: only the assigned supervisor can evaluate
    if request.user.email != attachment.supervisor_email:
        messages.error(request, "You are not assigned as supervisor for this student.")
        return redirect("evaluations:supervisor_dashboard")

    criteria_list = EvaluationCriteria.objects.all()

    # ✅ Load existing evaluation or None
    evaluation = SupervisorEvaluation.objects.filter(
        attachment=attachment, supervisor=request.user
    ).first()
    is_edit = evaluation is not None

    if request.method == "POST":
        form = SupervisorEvaluationForm(
            request.POST,
            instance=evaluation,
            criteria_list=criteria_list,
        )
        if form.is_valid():
            evaluation = form.save(commit=False)
            evaluation.attachment = attachment
            evaluation.supervisor = request.user

            # ✅ Save criteria scores in JSON
            evaluation.criteria_scores = {
                str(criteria.id): int(form.cleaned_data.get(f"criteria_{criteria.id}", 3))
                for criteria in criteria_list
            }

            # ✅ Draft vs Submit
            if "save_draft" in request.POST:
                evaluation.status = "draft"
                messages.info(request, "Draft saved successfully.")
            elif "submit" in request.POST:
                evaluation.status = "submitted"
                messages.success(request, "Evaluation submitted successfully!")

            evaluation.save()
            return redirect("evaluations:supervisor_dashboard")
    else:
        form = SupervisorEvaluationForm(
            instance=evaluation,
            criteria_list=criteria_list,
        )

    return render(request, "evaluations/evaluation_form.html", {
        "form": form,
        "attachment": attachment,
        "criteria_list": criteria_list,
        "is_edit": is_edit,
    })



# ---------------- Lecturer Views ---------------- #

@login_required
@role_required([3])  # Lecturers only
def lecturer_dashboard(request):
    """Lecturer dashboard shows all attachments and evaluations."""
    all_attachments = Attachment.objects.all()
    evaluations = LecturerEvaluation.objects.filter(lecturer=request.user)

    completed_attachments = [eval.attachment for eval in evaluations]
    pending_evaluations = all_attachments.count() - len(completed_attachments)

    return render(request, "evaluations/lecturer_dashboard.html", {
        "all_attachments": all_attachments,
        "evaluations": evaluations,
        "pending_evaluations": pending_evaluations,
    })


@login_required
@role_required([3])
def grading_panel(request, attachment_id):
    """Lecturer grades a student, referencing supervisor evaluation."""
    attachment = get_object_or_404(Attachment, id=attachment_id)
    criteria_list = EvaluationCriteria.objects.all()

    supervisor_evaluation = SupervisorEvaluation.objects.filter(attachment=attachment).first()

    existing_evaluation = LecturerEvaluation.objects.filter(
        attachment=attachment, lecturer=request.user
    ).first()

    if request.method == "POST":
        form = LecturerEvaluationForm(request.POST, instance=existing_evaluation, criteria_list=criteria_list)
        if form.is_valid():
            evaluation = form.save(commit=False)
            evaluation.attachment = attachment
            evaluation.lecturer = request.user

            # Optional: Save per-criteria scores
            evaluation.criteria_scores = {
                criteria.id: int(form.cleaned_data.get(f"criteria_{criteria.id}", 3))
                for criteria in criteria_list
            }
            evaluation.save()

            messages.success(request, "Evaluation submitted successfully!")
            return redirect("evaluations:lecturer_dashboard")
    else:
        form = LecturerEvaluationForm(instance=existing_evaluation, criteria_list=criteria_list)

    return render(request, "evaluations/grading_panel.html", {
        "attachment": attachment,
        "form": form,
        "supervisor_evaluation": supervisor_evaluation,
        "criteria_list": criteria_list,
    })
