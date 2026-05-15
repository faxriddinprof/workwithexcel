from pathlib import Path

from django import forms

from .models import ReportAssignment, ReportTemplate, Specialist


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
    region = forms.ChoiceField()
    due_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['template'].queryset = ReportTemplate.objects.all().order_by('-reporting_month', 'name')
        region_values = Specialist.objects.filter(
            type=Specialist.Type.REGIONAL_SPECIALIST,
            user__is_active=True,
        ).exclude(region='').values_list('region', flat=True).distinct().order_by('region')
        self.fields['region'].choices = [(region, region) for region in region_values]

    def clean_region(self):
        region = self.cleaned_data['region'].strip()
        if not Specialist.objects.filter(
            type=Specialist.Type.REGIONAL_SPECIALIST,
            user__is_active=True,
            region__iexact=region,
        ).exists():
            raise forms.ValidationError('No active regional specialist was found for this region.')
        return region


class ReportAssignmentFilterForm(forms.Form):
    region = forms.ChoiceField(required=False)
    status = forms.ChoiceField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        region_values = Specialist.objects.filter(
            type=Specialist.Type.REGIONAL_SPECIALIST,
            user__is_active=True,
        ).exclude(region='').values_list('region', flat=True).distinct().order_by('region')
        self.fields['region'].choices = [('', 'All regions'), *[(region, region) for region in region_values]]
        self.fields['status'].choices = [('', 'All statuses'), *ReportAssignment.Status.choices]