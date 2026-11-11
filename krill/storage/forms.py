from django import forms
from .models.storage import Device, Shelf, Rack, Box
from .models.site import Site
from sample.widgets import mark_comboboxes
from sample.widgets import mark_comboboxes

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
        fields = ['name', 'description', 'site', 'auto_store_enabled', 'access_level']
        help_texts = {
            'name': 'Name of this device',
            'description': 'Description of this device',
            'site': 'Site where this device is located',
            'auto_store_enabled': 'Enable auto-store for all boxes in this device',
            'access_level': 'Restrict access to specific user tiers',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make access_level optional by not requiring it
        self.fields['access_level'].required = False
        mark_comboboxes(self)
        mark_comboboxes(self)

class ShelfForm(forms.ModelForm):
    class Meta:
        model = Shelf
        fields = ['name', 'description', 'device', 'access_level']
        help_texts = {
            'name': 'Name of this shelf',
            'description': 'Description of this shelf',
            'device': 'Device where this shelf is located',
            'access_level': 'Restrict access to specific user tiers',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make access_level optional by not requiring it
        self.fields['access_level'].required = False
        mark_comboboxes(self)
        mark_comboboxes(self)

class RackForm(forms.ModelForm):
    class Meta:
        model = Rack
        fields = ['name', 'description', 'shelf', 'access_level']
        help_texts = {
            'name': 'Name of this rack',
            'description': 'Description of this rack',
            'shelf': 'Shelf where this rack is located',
            'access_level': 'Restrict access to specific user tiers',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make access_level optional by not requiring it
        self.fields['access_level'].required = False
        # "Device › Shelf": shelves in different devices can share a name
        self.fields['shelf'].queryset = Shelf.objects.select_related('device')
        self.fields['shelf'].label_from_instance = lambda shelf: f'{shelf.device.name} › {shelf.name}'
        mark_comboboxes(self)
        # "Device › Shelf": shelves in different devices can share a name
        self.fields['shelf'].queryset = Shelf.objects.select_related('device')
        self.fields['shelf'].label_from_instance = lambda shelf: f'{shelf.device.name} › {shelf.name}'
        mark_comboboxes(self)

class BoxForm(forms.ModelForm):
    class Meta:
        model = Box
        fields = ['name', 'description', 'rack', 'rows', 'columns', 'access_level']
        help_texts = {
            'name': 'Name of this box',
            'description': 'Description of this box',
            'rack': 'Rack where this box is located',
            'rows': 'Number of rows in this box',
            'columns': 'Number of columns in this box',
            'access_level': 'Restrict access to specific user tiers',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make access_level optional by not requiring it
        self.fields['access_level'].required = False
        # "Device › Shelf › Rack": racks in different shelves can share a name
        self.fields['rack'].queryset = Rack.objects.select_related('shelf__device')
        self.fields['rack'].label_from_instance = lambda rack: f'{rack.shelf.device.name} › {rack.shelf.name} › {rack.name}'
        mark_comboboxes(self)
        # "Device › Shelf › Rack": racks in different shelves can share a name
        self.fields['rack'].queryset = Rack.objects.select_related('shelf__device')
        self.fields['rack'].label_from_instance = lambda rack: f'{rack.shelf.device.name} › {rack.shelf.name} › {rack.name}'
        mark_comboboxes(self)
