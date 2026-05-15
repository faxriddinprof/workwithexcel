from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone


class Specialist(models.Model):
    class Type(models.IntegerChoices):
        HEAD_OFFICER = 1, 'Head Officer'
        REGIONAL_SPECIALIST = 2, 'Regional Specialist'

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='specialist')
    type = models.PositiveSmallIntegerField(choices=Type.choices)
    region = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['region', 'user__username']

    def __str__(self):
        label = self.get_type_display()
        return f'{self.user.get_username()} - {label} ({self.region or "No region"})'

    @property
    def display_name(self):
        return self.user.get_full_name() or self.user.get_username()


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
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        IN_PROGRESS = 'in_progress', 'In Progress'
        SUBMITTED = 'submitted', 'Submitted'

    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE, related_name='assignments')
    specialist = models.ForeignKey(Specialist, on_delete=models.CASCADE, related_name='assignments', null=True, blank=True)
    assigned_by = models.ForeignKey(
        Specialist,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_assignments',
    )
    region = models.CharField(max_length=100, blank=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    progress = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_date', '-updated_at']
        constraints = [
            models.UniqueConstraint(fields=['template', 'specialist'], name='unique_template_specialist'),
        ]

    def __str__(self):
        return f'{self.template.name} -> {self.region or self.specialist}'

    @property
    def assigned_user(self):
        return self.specialist.user if self.specialist_id else None


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