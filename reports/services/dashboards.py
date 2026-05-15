from django.db.models import Count

from ..models import ReportAssignment, ReportTemplate, Specialist


def build_head_officer_dashboard_context():
    assignments = ReportAssignment.objects.select_related('template', 'specialist', 'specialist__user').all()
    total_assignments = assignments.count()
    submitted_count = assignments.filter(status=ReportAssignment.Status.SUBMITTED).count()

    return {
        'stats': {
            'templates': ReportTemplate.objects.count(),
            'assignments': total_assignments,
            'submitted': submitted_count,
            'completion_rate': round((submitted_count / total_assignments) * 100) if total_assignments else 0,
        },
        'recent_templates': ReportTemplate.objects.order_by('-created_at')[:5],
        'recent_assignments': assignments.order_by('-created_at')[:8],
        'regional_distribution': Specialist.objects.filter(type=Specialist.Type.REGIONAL_SPECIALIST).values('region').annotate(total=Count('assignments')).order_by('region'),
    }


def build_regional_dashboard_context(specialist):
    assignments = ReportAssignment.objects.filter(specialist=specialist).select_related('template').prefetch_related('submission')
    total_assignments = assignments.count()
    submitted_count = assignments.filter(status=ReportAssignment.Status.SUBMITTED).count()

    return {
        'stats': {
            'assigned': total_assignments,
            'submitted': submitted_count,
            'in_progress': assignments.filter(status=ReportAssignment.Status.IN_PROGRESS).count(),
            'pending': assignments.filter(status=ReportAssignment.Status.PENDING).count(),
        },
        'assignments': assignments.order_by('due_date', '-updated_at'),
        'completion_rate': round((submitted_count / total_assignments) * 100) if total_assignments else 0,
    }