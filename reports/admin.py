from django.contrib import admin

from .models import ReportAssignment, ReportSubmission, ReportTemplate, Specialist


@admin.register(Specialist)
class SpecialistAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'region', 'created_at')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'region')
    list_filter = ('type', 'region')
    list_select_related = ('user',)


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'report_type', 'reporting_month', 'column_count', 'created_at')
    search_fields = ('name', 'report_type')
    list_filter = ('report_type', 'reporting_month')


@admin.register(ReportAssignment)
class ReportAssignmentAdmin(admin.ModelAdmin):
    list_display = ('template', 'region', 'specialist', 'due_date', 'status', 'progress')
    search_fields = ('template__name', 'specialist__user__username', 'region')
    list_filter = ('status', 'region')
    list_select_related = ('template', 'specialist', 'specialist__user')


@admin.register(ReportSubmission)
class ReportSubmissionAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'status', 'submitted_at', 'updated_at')
    search_fields = ('assignment__template__name', 'assignment__specialist__user__username')
    list_filter = ('status',)
    list_select_related = ('assignment', 'assignment__template', 'assignment__specialist', 'assignment__specialist__user')