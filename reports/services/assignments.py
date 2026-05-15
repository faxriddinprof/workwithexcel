from django.core.exceptions import ValidationError

from ..models import ReportAssignment, Specialist


def find_regional_specialist(region):
    return Specialist.objects.select_related('user').filter(
        type=Specialist.Type.REGIONAL_SPECIALIST,
        user__is_active=True,
        region__iexact=region,
    ).first()


def create_assignment_from_region(*, template, region, due_date, assigned_by=None):
    specialist = find_regional_specialist(region)
    if specialist is None:
        raise ValidationError('No active regional specialist exists for the selected region.')

    assignment, created = ReportAssignment.objects.get_or_create(
        template=template,
        specialist=specialist,
        defaults={
            'region': specialist.region,
            'due_date': due_date,
            'assigned_by': assigned_by,
            'status': ReportAssignment.Status.PENDING,
            'progress': 0,
        },
    )

    if not created:
        assignment.region = specialist.region
        assignment.due_date = due_date
        assignment.assigned_by = assigned_by
        assignment.save(update_fields=['region', 'due_date', 'assigned_by', 'updated_at'])

    return assignment, created


def calculate_progress(rows, structure, submission_status):
    if submission_status == 'submitted':
        return 100

    columns = [column for column in structure.get('columns', []) if not column.get('is_formula')]
    if not rows or not columns:
        return 0

    total_cells = len(rows) * len(columns)
    filled_cells = 0
    for row in rows:
        for column in columns:
            value = row.get(column['key'], '')
            if value not in (None, ''):
                filled_cells += 1
    return round((filled_cells / total_cells) * 100) if total_cells else 0


def derive_assignment_status(rows, submission_status):
    if submission_status == 'submitted':
        return ReportAssignment.Status.SUBMITTED
    if rows:
        return ReportAssignment.Status.IN_PROGRESS
    return ReportAssignment.Status.PENDING