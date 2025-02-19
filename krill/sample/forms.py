from django import forms
from .models.sample import Sample
from .models.aliquot import Aliquot, AliquotType, AliquotDisposition

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
        fields = ['sample', 'quantity', 'box', 'row', 'column', 'aliquotType', 'disposition', 'passage', 'notes']
        help_texts = {
            'sample': 'Parent sample',
            'quantity': 'Amount of sample in this aliquot',
            'box': 'Storage box location',
            'row': 'Row position in box',
            'column': 'Column position in box',
            'aliquotType': 'Type of aliquot',
            'disposition': 'Current status of the aliquot',
            'passage': 'Passage number',
            'notes': 'Additional notes about the aliquot',
        }
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 4}),
        }

class AliquotTypeForm(forms.ModelForm):
    class Meta:
        model = AliquotType
        fields = ['name', 'description']
        help_texts = {
            'name': 'Name of the aliquot type',
            'description': 'Description of this type of aliquot',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class AliquotDispositionForm(forms.ModelForm):
    class Meta:
        model = AliquotDisposition
        fields = ['name', 'dispositionType', 'description']
        help_texts = {
            'name': 'Name of the disposition',
            'dispositionType': 'Type of disposition (Stored, Exhausted, In Use)',
            'description': 'Description of this disposition',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        } 