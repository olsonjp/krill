from django import forms
from .models.sample import Sample
from .models.aliquot import Aliquot, AliquotLocation, AliquotType, AliquotDisposition, AliquotTube
from .models.source import Source
class SampleForm(forms.ModelForm):
    class Meta:
        model = Sample
        fields = ['name', 'source', 'notes']
        help_texts = {
            'name': 'Unique identifier for the sample',
            'source': 'Source of the sample',
            'notes': 'Additional information about the sample',
        }
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 4}),
        }

class AliquotForm(forms.ModelForm):
    class Meta:
        model = Aliquot
        fields = ['parent', 'sample', 'quantity', 'aliquotType', 
                 'passage', 'experiment', 'notes']
        help_texts = {
            'parent': 'Parent aliquot, if this is a derivative',
            'sample': 'Sample this aliquot belongs to',
            'quantity': 'Quantity of the aliquot',
            'aliquotType': 'Type of aliquot',
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
        # Set the queryset for boxes
        self.fields['box'].queryset = Box.objects.all().order_by('name')
    
    def clean(self):
        cleaned_data = super().clean()
        box = cleaned_data.get('box')
        row = cleaned_data.get('row')
        column = cleaned_data.get('column')
        
        if box and row and column:
            # Check if the position is within the box dimensions
            if row > box.rows:
                raise forms.ValidationError(f"Row {row} is outside the box dimensions (max: {box.rows})")
            if column > box.columns:
                raise forms.ValidationError(f"Column {column} is outside the box dimensions (max: {box.columns})")
            
            # Check if the position is already occupied
            if AliquotLocation.objects.filter(box=box, row=row, column=column).exists():
                raise forms.ValidationError(f"Position ({row}, {column}) in {box.name} is already occupied")
        
        return cleaned_data 