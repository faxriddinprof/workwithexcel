from datetime import date
from pathlib import Path

from django import forms
from django.contrib.auth import get_user_model

from .models import ReportTemplate

User = get_user_model()


class MonthInput(forms.DateInput):
    input_type = 'month'


class ReportTemplateForm(forms.ModelForm):
    reporting_month = forms.DateField(
        input_formats=['%Y-%m', '%Y-%m-%d'],
        widget=MonthInput(),
    )

    class Meta:
        model = ReportTemplate
        fields = ['name', 'report_type', 'reporting_month', 'excel_file']

    def clean_reporting_month(self):
        reporting_month = self.cleaned_data['reporting_month']
        return reporting_month.replace(day=1)

    def clean_excel_file(self):
        excel_file = self.cleaned_data['excel_file']
        suffix = Path(excel_file.name).suffix.lower()
        if suffix not in {'.xlsx', '.xlsm'}:
            raise forms.ValidationError('Upload an .xlsx or .xlsm file.')
        if excel_file.size > 5 * 1024 * 1024:
            raise forms.ValidationError('File size must be below 5 MB for this prototype.')
        return excel_file


class ReportAssignmentForm(forms.Form):
    template = forms.ModelChoiceField(queryset=ReportTemplate.objects.all())
    assignees = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True, is_staff=False),
        widget=forms.CheckboxSelectMultiple,
    )
    due_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['template'].queryset = ReportTemplate.objects.all()
        self.fields['assignees'].queryset = User.objects.filter(is_active=True, is_staff=False).order_by('username')