from django.contrib import admin

from .models import ReportAssignment, ReportSubmission, ReportTemplate


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'report_type', 'reporting_month', 'column_count', 'created_at')
    search_fields = ('name', 'report_type')
    list_filter = ('report_type', 'reporting_month')


@admin.register(ReportAssignment)
class ReportAssignmentAdmin(admin.ModelAdmin):
    list_display = ('template', 'assignee', 'due_date', 'created_at')
    search_fields = ('template__name', 'assignee__username')
    list_select_related = ('template', 'assignee')


@admin.register(ReportSubmission)
class ReportSubmissionAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'status', 'submitted_at', 'updated_at')
    search_fields = ('assignment__template__name', 'assignment__assignee__username')
    list_filter = ('status',)
    list_select_related = ('assignment', 'assignment__template', 'assignment__assignee')