from django import forms
from django.contrib.auth.models import User
from .models import ReportTemplate, Alert


class ReportGenerationForm(forms.Form):
    """Form for generating reports"""
    template = forms.ModelChoiceField(
        queryset=ReportTemplate.objects.filter(is_active=True),
        empty_label="Select a report template",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Report name'})
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional description'})
    )
    format = forms.ChoiceField(
        choices=Report.FORMAT_CHOICES,
        initial='pdf',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add custom validation or field customization here


class AlertCreationForm(forms.ModelForm):
    """Form for creating alerts"""
    class Meta:
        model = Alert
        fields = ['title', 'message', 'severity', 'alert_type', 'target_type', 'target_id']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Alert title'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Alert message'}),
            'severity': forms.Select(attrs={'class': 'form-control'}),
            'alert_type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., storage_full, temperature_warning'}),
            'target_type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., freezer, sample (optional)'}),
            'target_id': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Target ID (optional)'}),
        }





class SampleSearchForm(forms.Form):
    """Form for searching samples"""
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name, description, or type...'
        })
    )
    sample_type = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filter by sample type'
        })
    )
    disposition = forms.ChoiceField(
        required=False,
        choices=[('', 'All dispositions')] + [
            ('stored', 'Stored'),
            ('in_use', 'In Use'),
            ('exhausted', 'Exhausted'),
            ('disposed', 'Disposed'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        query = cleaned_data.get('query')
        sample_type = cleaned_data.get('sample_type')
        disposition = cleaned_data.get('disposition')
        
        # At least one filter must be provided
        if not any([query, sample_type, disposition]):
            raise forms.ValidationError("Please provide at least one search criteria.")
        
        return cleaned_data


class ReportTemplateForm(forms.ModelForm):
    """Form for creating/editing report templates"""
    class Meta:
        model = ReportTemplate
        fields = ['name', 'description', 'report_type', 'template_data', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Template name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Template description'}),
            'report_type': forms.Select(attrs={'class': 'form-control'}),
            'template_data': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 8,
                'placeholder': 'JSON configuration for the report template'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_template_data(self):
        """Validate that template_data is valid JSON"""
        import json
        template_data = self.cleaned_data.get('template_data')
        if template_data:
            try:
                json.loads(template_data)
            except json.JSONDecodeError:
                raise forms.ValidationError("Template data must be valid JSON.")
        return template_data


class ScheduledReportForm(forms.ModelForm):
    """Form for creating/editing scheduled reports"""
    class Meta:
        model = ScheduledReport
        fields = ['name', 'description', 'template', 'frequency', 'parameters', 'recipients', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Scheduled report name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Description'}),
            'template': forms.Select(attrs={'class': 'form-control'}),
            'frequency': forms.Select(attrs={'class': 'form-control'}),
            'parameters': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'JSON parameters for the report'
            }),
            'recipients': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'One email address per line'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_recipients(self):
        """Convert recipients text to list and validate emails"""
        recipients_text = self.cleaned_data.get('recipients')
        if recipients_text:
            recipients = [email.strip() for email in recipients_text.split('\n') if email.strip()]
            # Basic email validation
            from django.core.validators import validate_email
            for email in recipients:
                try:
                    validate_email(email)
                except forms.ValidationError:
                    raise forms.ValidationError(f"Invalid email address: {email}")
            return recipients
        return []
    
    def clean_parameters(self):
        """Validate that parameters is valid JSON"""
        import json
        parameters = self.cleaned_data.get('parameters')
        if parameters:
            try:
                json.loads(parameters)
            except json.JSONDecodeError:
                raise forms.ValidationError("Parameters must be valid JSON.")
        return parameters
