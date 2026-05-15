import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import ReportAssignmentForm, ReportTemplateForm
from .models import ReportAssignment, ReportSubmission, ReportTemplate
from .services.excel import export_submission_workbook, normalize_submission_rows, parse_template_structure, rows_for_grid


staff_required = user_passes_test(lambda user: user.is_staff)


@login_required
def dashboard(request):
    if request.user.is_staff:
        context = {
            'templates': ReportTemplate.objects.prefetch_related('assignments')[:10],
            'assignments': ReportAssignment.objects.select_related('template', 'assignee')[:12],
            'submissions': ReportSubmission.objects.select_related('assignment', 'assignment__template', 'assignment__assignee')[:12],
        }
    else:
        context = {
            'assignments': ReportAssignment.objects.filter(assignee=request.user).select_related('template').prefetch_related('submission'),
        }
    return render(request, 'reports/dashboard.html', context)


@staff_required
def template_upload(request):
    if request.method == 'POST':
        form = ReportTemplateForm(request.POST, request.FILES)
        if form.is_valid():
            report_template = form.save(commit=False)
            report_template.created_by = request.user
            report_template.structure = parse_template_structure(form.cleaned_data['excel_file'])
            report_template.save()
            messages.success(request, 'Template uploaded and parsed successfully.')
            return redirect('reports:dashboard')
    else:
        form = ReportTemplateForm()
    return render(request, 'reports/template_upload.html', {'form': form})


@staff_required
def assignment_create(request):
    if request.method == 'POST':
        form = ReportAssignmentForm(request.POST)
        if form.is_valid():
            template = form.cleaned_data['template']
            due_date = form.cleaned_data['due_date']
            created_count = 0
            for assignee in form.cleaned_data['assignees']:
                assignment, created = ReportAssignment.objects.get_or_create(
                    template=template,
                    assignee=assignee,
                    defaults={'due_date': due_date, 'assigned_by': request.user},
                )
                if not created and due_date:
                    assignment.due_date = due_date
                    assignment.assigned_by = request.user
                    assignment.save(update_fields=['due_date', 'assigned_by'])
                created_count += int(created)
            messages.success(request, f'Assignments processed. Created {created_count} new assignments.')
            return redirect('reports:dashboard')
    else:
        form = ReportAssignmentForm()
    return render(request, 'reports/assignment_form.html', {'form': form})


@login_required
def submission_editor(request, assignment_id):
    assignment = get_assignment_for_user(request.user, assignment_id)
    submission, _ = ReportSubmission.objects.get_or_create(assignment=assignment)
    structure = assignment.template.structure

    context = {
        'assignment': assignment,
        'submission': submission,
        'grid_columns': structure.get('columns', []),
        'grid_data': rows_for_grid(submission.submitted_data, structure),
    }
    return render(request, 'reports/submission_editor.html', context)


@login_required
@require_POST
def submission_save(request, assignment_id):
    assignment = get_assignment_for_user(request.user, assignment_id)
    submission, _ = ReportSubmission.objects.get_or_create(assignment=assignment)

    try:
        payload = json.loads(request.body.decode('utf-8'))
        normalized_rows = normalize_submission_rows(payload.get('rows', []), assignment.template.structure)
    except (json.JSONDecodeError, ValidationError) as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=400)

    submission.submitted_data = normalized_rows
    submission.status = payload.get('status') or ReportSubmission.Status.DRAFT
    submission.metadata = {'row_count': len(normalized_rows)}
    if submission.status == ReportSubmission.Status.SUBMITTED:
        submission.submitted_at = timezone.now()
    submission.save()
    return JsonResponse({'ok': True, 'updated_at': submission.updated_at.isoformat()})


@login_required
def submission_export(request, assignment_id):
    assignment = get_assignment_for_user(request.user, assignment_id)
    submission, _ = ReportSubmission.objects.get_or_create(assignment=assignment)
    workbook = export_submission_workbook(assignment.template, submission.submitted_data)
    filename = f'{assignment.template.report_type}_{assignment.assignee.username}_{assignment.template.reporting_month:%Y_%m}.xlsx'
    return FileResponse(workbook, as_attachment=True, filename=filename)


def get_assignment_for_user(user, assignment_id):
    assignment = get_object_or_404(ReportAssignment.objects.select_related('template', 'assignee'), pk=assignment_id)
    if not user.is_staff and assignment.assignee != user:
        raise PermissionDenied('You do not have access to this report assignment.')
    return assignment