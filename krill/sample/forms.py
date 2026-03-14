from django import forms
from .models.sample import Sample
from .models.aliquot import Aliquot, AliquotLocation, AliquotType, AliquotDisposition
from .models.source import Source

class SampleForm(forms.ModelForm):
    class Meta:
        model = Sample
        fields = ['name', 'experiment', 'source', 'notes', 'access_level']
        help_texts = {
            'name': 'Unique identifier for this sample (e.g., cell line name)',
            'experiment': 'Experiment identifier or number associated with this sample',
            'source': 'Lab or origin of the sample',
            'notes': 'Additional information about the sample',
            'access_level': 'Restrict access to specific user tiers',
        }
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 4}),
        }

class AliquotForm(forms.ModelForm):
    # count: number of aliquots to create at once (not a model field)
    count = forms.IntegerField(
        required=False,
        initial=1,
        min_value=1,
        help_text='Number of aliquots to create at once'
    )
    # Optional box assignment fields (not part of the model)
    assign_to_box = forms.BooleanField(
        required=False,
        initial=False,
        help_text='Assign aliquots to a storage box immediately after creation'
    )
    box = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        required=False,
        empty_label="Select a storage box",
        help_text="Choose the box to store aliquots in"
    )
    start_row = forms.IntegerField(
        required=False,
        min_value=1,
        help_text="Starting row position (leave empty to auto-assign)"
    )
    start_column = forms.IntegerField(
        required=False,
        min_value=1,
        help_text="Starting column position (leave empty to auto-assign)"
    )

    class Meta:
        model = Aliquot
        fields = ['parent', 'sample', 'aliquot_type', 'disposition', 'access_level']
        help_texts = {
            'parent': 'Parent aliquot, if this is a derivative',
            'sample': 'Sample this aliquot belongs to',
            'aliquot_type': 'Type of aliquot',
            'disposition': 'Current status of this aliquot',
            'access_level': 'Restrict access to specific user tiers',
        }

    def __init__(self, *args, **kwargs):
        from storage.models.storage import Box
        super().__init__(*args, **kwargs)
        self.fields['box'].queryset = Box.objects.all().order_by('name')

    def clean(self):
        """Validate box assignment fields"""
        cleaned_data = super().clean()
        assign_to_box = cleaned_data.get('assign_to_box')
        box = cleaned_data.get('box')
        start_row = cleaned_data.get('start_row')
        start_column = cleaned_data.get('start_column')

        if assign_to_box and box:
            # Validate start_row if provided
            if start_row is not None:
                if start_row < 1:
                    raise forms.ValidationError({
                        'start_row': 'Row must be at least 1.'
                    })
                if start_row > box.rows:
                    raise forms.ValidationError({
                        'start_row': f'Row must not exceed box dimensions (max: {box.rows}).'
                    })

            # Validate start_column if provided
            if start_column is not None:
                if start_column < 1:
                    raise forms.ValidationError({
                        'start_column': 'Column must be at least 1.'
                    })
                if start_column > box.columns:
                    raise forms.ValidationError({
                        'start_column': f'Column must not exceed box dimensions (max: {box.columns}).'
                    })

        return cleaned_data

class AliquotLocationForm(forms.ModelForm):
    class Meta:
        model = AliquotLocation
        fields = ['aliquot', 'box', 'row', 'column']
        help_texts = {
            'aliquot': 'Aliquot to locate',
            'box': 'Storage box',
            'row': 'Row position (1-10)',
            'column': 'Column position (1-10)',
        }

class AliquotTypeForm(forms.ModelForm):
    class Meta:
        model = AliquotType
        fields = ['name', 'description']
        help_texts = {
            'name': 'Name of this aliquot type',
            'description': 'Description of this type',
        }

class AliquotDispositionForm(forms.ModelForm):
    class Meta:
        model = AliquotDisposition
        fields = ['name', 'disposition_type']
        help_texts = {
            'name': 'Name of this disposition',
            'disposition_type': 'Type of disposition',
        }

class SourceForm(forms.ModelForm):
    class Meta:
        model = Source
        fields = ['name', 'description']

class AliquotMoveForm(forms.Form):
    """Form for moving an aliquot to a new storage location"""
    box = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        empty_label="Select a storage box",
        help_text="Choose the box to move the aliquot to"
    )
    row = forms.IntegerField(
        min_value=1,
        max_value=10,
        help_text="Row position (1-10)"
    )
    column = forms.IntegerField(
        min_value=1,
        max_value=10,
        help_text="Column position (1-10)"
    )

    def __init__(self, *args, **kwargs):
        from storage.models.storage import Box
        super().__init__(*args, **kwargs)
        self.fields['box'].queryset = Box.objects.all()
