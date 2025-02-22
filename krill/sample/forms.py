from django import forms
from .models.sample import Sample
from .models.aliquot import Aliquot, AliquotLocation, AliquotType, AliquotDisposition
from .models.source import Source
class SampleForm(forms.ModelForm):
    class Meta:
        model = Sample
        fields = ['name', 'notes']
        help_texts = {
            'name': 'Unique identifier for the sample',
            'notes': 'Additional information about the sample',
        }
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 4}),
        }

class AliquotForm(forms.ModelForm):
    class Meta:
        model = Aliquot
        fields = ['parent', 'sample', 'quantity', 'aliquotType', 'disposition', 
                 'passage', 'experiment', 'notes']
        help_texts = {
            'parent': 'Parent aliquot, if this is a derivative',
            'sample': 'Sample this aliquot belongs to',
            'quantity': 'Quantity of the aliquot',
            'aliquotType': 'Type of aliquot',
            'disposition': 'Current disposition of the aliquot',
            'passage': 'Passage number',
            'experiment': 'Experiment details',
            'notes': 'Additional notes',
        }
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 4}),
            'experiment': forms.Textarea(attrs={'rows': 4}),
        }

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
        fields = ['name', 'dispositionType', 'description']
        help_texts = {
            'name': 'Name of this disposition',
            'dispositionType': 'Type of disposition',
            'description': 'Description of this disposition',
        }

class SourceForm(forms.ModelForm):
    class Meta:
        model = Source
        fields = ['name', 'description'] 