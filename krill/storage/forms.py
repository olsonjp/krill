from django import forms
from .models.storage import Device, Shelf, Rack, Box
from .models.site import Site

class SiteForm(forms.ModelForm):
    class Meta:
        model = Site
        fields = ['name', 'description']
        help_texts = {
            'name': 'Name of this site',
            'description': 'Description of this site',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = ['name', 'description', 'site']
        help_texts = {
            'name': 'Name of this device',
            'description': 'Description of this device',
            'site': 'Site where this device is located',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class ShelfForm(forms.ModelForm):
    class Meta:
        model = Shelf
        fields = ['name', 'description', 'device']
        help_texts = {
            'name': 'Name of this shelf',
            'description': 'Description of this shelf',
            'device': 'Device where this shelf is located',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class RackForm(forms.ModelForm):
    class Meta:
        model = Rack
        fields = ['name', 'description', 'shelf']
        help_texts = {
            'name': 'Name of this rack',
            'description': 'Description of this rack',
            'shelf': 'Shelf where this rack is located',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class BoxForm(forms.ModelForm):
    class Meta:
        model = Box
        fields = ['name', 'description', 'rack', 'rows', 'columns']
        help_texts = {
            'name': 'Name of this box',
            'description': 'Description of this box',
            'rack': 'Rack where this box is located',
            'rows': 'Number of rows in this box',
            'columns': 'Number of columns in this box',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        } 