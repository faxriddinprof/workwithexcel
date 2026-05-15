import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .decorators import get_current_specialist, head_officer_required, is_head_officer_user
from .forms import ReportAssignmentFilterForm, ReportAssignmentForm, ReportTemplateForm
from .models import ReportAssignment, ReportSubmission, ReportTemplate
from .services.assignments import calculate_progress, create_assignment_from_region, derive_assignment_status
from .services.dashboards import build_head_officer_dashboard_context, build_regional_dashboard_context
from .services.excel import export_submission_workbook, normalize_submission_rows, parse_template_structure, rows_for_grid


@login_required
def dashboard(request):
    if is_head_officer_user(request.user):
        return redirect('reports:head_officer_dashboard')
    return redirect('reports:regional_dashboard')


@head_officer_required
def head_officer_dashboard(request):
    context = build_head_officer_dashboard_context()
    return render(request, 'reports/dashboards/head_officer_dashboard.html', context)


@login_required
def regional_dashboard(request):
    specialist = require_regional_specialist(request.user)
    context = build_regional_dashboard_context(specialist)
    return render(request, 'reports/dashboards/regional_dashboard.html', context)


@head_officer_required
def template_upload(request):
    saved_template = None
    if request.method == 'POST':
        form = ReportTemplateForm(request.POST, request.FILES)
        if form.is_valid():
            report_template = form.save(commit=False)
            report_template.created_by = request.user
            report_template.structure = parse_template_structure(form.cleaned_data['excel_file'])
            report_template.save()
            messages.success(request, 'Template uploaded and parsed successfully.')
            return redirect(f"{request.path}?template_id={report_template.id}")
    else:
        form = ReportTemplateForm()
        template_id = request.GET.get('template_id')
        if template_id:
            saved_template = ReportTemplate.objects.filter(pk=template_id).first()
    return render(request, 'reports/template_upload.html', {'form': form, 'saved_template': saved_template})


@head_officer_required
def assignment_create(request):
    current_specialist = get_current_specialist(request.user)
    if request.method == 'POST':
        form = ReportAssignmentForm(request.POST)
        if form.is_valid():
            assignment, created = create_assignment_from_region(
                template=form.cleaned_data['template'],
                region=form.cleaned_data['region'],
                due_date=form.cleaned_data['due_date'],
                assigned_by=current_specialist,
            )
            messages.success(request, f'Report assigned to {assignment.specialist.display_name}.')
            if not created:
                messages.info(request, 'Existing assignment was updated with the new deadline.')
            return redirect('reports:assigned_reports')
    else:
        form = ReportAssignmentForm()
    return render(request, 'reports/assignment_form.html', {'form': form})


@head_officer_required
def assigned_reports_list(request):
    form = ReportAssignmentFilterForm(request.GET or None)
    assignments = ReportAssignment.objects.select_related('template', 'specialist', 'specialist__user').all()
    if form.is_valid():
        region = form.cleaned_data.get('region')
        status = form.cleaned_data.get('status')
        if region:
            assignments = assignments.filter(region__iexact=region)
        if status:
            assignments = assignments.filter(status=status)

    total = assignments.count()
    submitted = assignments.filter(status=ReportAssignment.Status.SUBMITTED).count()
    context = {
        'form': form,
        'assignments': assignments.order_by('due_date', '-updated_at'),
        'stats': {
            'total': total,
            'submitted': submitted,
            'in_progress': assignments.filter(status=ReportAssignment.Status.IN_PROGRESS).count(),
            'pending': assignments.filter(status=ReportAssignment.Status.PENDING).count(),
            'completion_rate': round((submitted / total) * 100) if total else 0,
        },
    }
    return render(request, 'reports/assigned_reports_list.html', context)


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
        'grid_formulas': structure.get('formulas', []),
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

    requested_status = payload.get('status') or ReportSubmission.Status.DRAFT
    submission.submitted_data = normalized_rows
    submission.status = requested_status
    submission.metadata = {'row_count': len(normalized_rows)}
    assignment.progress = calculate_progress(normalized_rows, assignment.template.structure, requested_status)
    assignment.status = derive_assignment_status(normalized_rows, requested_status)
    if submission.status == ReportSubmission.Status.SUBMITTED:
        submission.submitted_at = timezone.now()
    elif not normalized_rows:
        submission.submitted_at = None
    assignment.save(update_fields=['progress', 'status', 'updated_at'])
    submission.save()
    return JsonResponse({'ok': True, 'updated_at': submission.updated_at.isoformat(), 'assignment_status': assignment.get_status_display(), 'progress': assignment.progress})


@login_required
def submission_export(request, assignment_id):
    assignment = get_assignment_for_user(request.user, assignment_id)
    submission, _ = ReportSubmission.objects.get_or_create(assignment=assignment)
    workbook = export_submission_workbook(assignment.template, submission.submitted_data)
    filename = f'{assignment.template.report_type}_{assignment.specialist.user.username}_{assignment.template.reporting_month:%Y_%m}.xlsx'
    return FileResponse(workbook, as_attachment=True, filename=filename)


def get_assignment_for_user(user, assignment_id):
    assignment = get_object_or_404(ReportAssignment.objects.select_related('template', 'specialist', 'specialist__user'), pk=assignment_id)
    if not is_head_officer_user(user) and assignment.specialist and assignment.specialist.user != user:
        raise PermissionDenied('You do not have access to this report assignment.')
    return assignment


def require_regional_specialist(user):
    specialist = get_current_specialist(user)
    if specialist and specialist.type == specialist.Type.REGIONAL_SPECIALIST:
        return specialist
    raise PermissionDenied('This page is only available to regional specialists.')