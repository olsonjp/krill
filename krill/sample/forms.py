from django import forms
from .models.sample import Sample
from .models.aliquot import Aliquot, AliquotLocation, AliquotType, AliquotDisposition, AliquotTube
from .models.source import Source

class SampleForm(forms.ModelForm):
    class Meta:
        model = Sample
        fields = ['name', 'source', 'notes', 'access_level']
        help_texts = {
            'name': 'Unique identifier for the sample',
            'source': 'Source of the sample',
            'notes': 'Additional information about the sample',
            'access_level': 'Restrict access to specific user tiers',
        }
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 4}),
        }

class AliquotForm(forms.ModelForm):
    class Meta:
        model = Aliquot
        fields = ['parent', 'sample', 'quantity', 'aliquot_type', 'access_level']
        help_texts = {
            'parent': 'Parent aliquot, if this is a derivative',
            'sample': 'Sample this aliquot belongs to',
            'quantity': 'Quantity of the aliquot',
            'aliquot_type': 'Type of aliquot',
            'access_level': 'Restrict access to specific user tiers',
        }
        widgets = {
            'quantity': forms.NumberInput(attrs={'min': 1}),
        }

class AliquotLocationForm(forms.ModelForm):
    class Meta:
        model = AliquotLocation
        fields = ['aliquot', 'box', 'row', 'column', 'tube_number']
        help_texts = {
            'aliquot': 'Aliquot to locate',
            'box': 'Storage box',
            'row': 'Row position (1-10)',
            'column': 'Column position (1-10)',
            'tube_number': 'Tube number within the aliquot',
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

class AliquotTubeForm(forms.ModelForm):
    class Meta:
        model = AliquotTube
        fields = ['disposition']
        help_texts = {
            'disposition': 'Current status of this tube',
        } 

class AliquotTubeMoveForm(forms.Form):
    box = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        empty_label="Select a storage box",
        help_text="Choose the box to move the tube to"
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