from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone


class ReportTemplate(models.Model):
    name = models.CharField(max_length=255)
    report_type = models.CharField(max_length=100)
    reporting_month = models.DateField(default=timezone.now)
    excel_file = models.FileField(
        upload_to='report_templates/%Y/%m/',
        validators=[FileExtensionValidator(allowed_extensions=['xlsx', 'xlsm'])],
    )
    structure = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_report_templates',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-reporting_month', '-created_at']

    def __str__(self):
        return f'{self.name} ({self.reporting_month:%Y-%m})'

    @property
    def column_count(self):
        return len(self.structure.get('columns', []))


class ReportAssignment(models.Model):
    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE, related_name='assignments')
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='report_assignments')
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_reports',
    )
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['template', 'assignee'], name='unique_template_assignee'),
        ]

    def __str__(self):
        return f'{self.template.name} -> {self.assignee}'


class ReportSubmission(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        SUBMITTED = 'submitted', 'Submitted'

    assignment = models.OneToOneField(ReportAssignment, on_delete=models.CASCADE, related_name='submission')
    submitted_data = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    metadata = models.JSONField(default=dict, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f'Submission for {self.assignment}'