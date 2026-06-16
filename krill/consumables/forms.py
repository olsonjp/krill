from django import forms
from .models.consumable import Consumable
from .models.consumable_type import ConsumableType
from .models.location import ConsumableRoom, ConsumableLocation
from .models.vendor import Vendor


class ConsumableForm(forms.ModelForm):
    class Meta:
        model = Consumable
        fields = [
            'name', 'consumable_type', 'vendor', 'catalog_number', 'lot_number',
            'location', 'quantity', 'unit', 'low_stock_threshold',
            'expiration_date', 'notes', 'access_level',
        ]
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 4}),
            'expiration_date': forms.DateInput(attrs={'type': 'date'}),
        }
        help_texts = {
            'name': 'Name or common abbreviation of this item',
            'consumable_type': 'Category of this item',
            'vendor': 'Supplier or manufacturer',
            'catalog_number': 'Vendor catalog / product number',
            'lot_number': 'Lot or batch number from the label',
            'location': 'Where this item is physically stored',
            'quantity': 'Current quantity on hand',
            'unit': 'Unit of measure (e.g. vials, mL, boxes)',
            'low_stock_threshold': 'Alert when quantity falls to or below this value',
            'expiration_date': 'Expiration date from the label',
            'notes': 'Any additional notes',
            'access_level': 'Restrict visibility to specific user tiers',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['access_level'].required = False
        self.fields['vendor'].required = False
        self.fields['location'].required = False

        ctype = self._resolve_type(args, kwargs)
        self.spec_field_names = []
        if ctype:
            for spec in ctype.spec_schema:
                fname = f"spec__{spec['name']}"
                field = self._build_field(spec)
                self.fields[fname] = field
                self.spec_field_names.append(fname)
                if self.instance and self.instance.pk:
                    self.fields[fname].initial = self.instance.specs.get(spec['name'])

    def _resolve_type(self, args, kwargs):
        # 1. From POST data
        data = args[0] if args else kwargs.get('data')
        if data and data.get('consumable_type'):
            try:
                return ConsumableType.objects.get(pk=data['consumable_type'])
            except (ConsumableType.DoesNotExist, ValueError):
                pass
        # 2. From existing instance
        if self.instance and self.instance.pk and self.instance.consumable_type_id:
            return self.instance.consumable_type
        # 3. From GET param stored in initial
        initial_type = self.initial.get('consumable_type')
        if initial_type:
            try:
                return ConsumableType.objects.get(pk=initial_type)
            except (ConsumableType.DoesNotExist, ValueError):
                pass
        # 4. First type alphabetically
        return ConsumableType.objects.order_by('name').first()

    def _build_field(self, spec):
        t = spec.get('type', 'text')
        common = {
            'required': spec.get('required', False),
            'label': spec.get('label', spec['name']),
            'help_text': spec.get('help', ''),
        }
        if t == 'number':
            return forms.DecimalField(max_digits=12, decimal_places=4, **common)
        if t == 'date':
            return forms.DateField(
                widget=forms.DateInput(attrs={'type': 'date'}), **common
            )
        if t == 'boolean':
            return forms.BooleanField(**common)
        if t == 'choice':
            choices = [('', '---')] + [(c, c) for c in spec.get('choices', [])]
            return forms.ChoiceField(choices=choices, **common)
        if t == 'textarea':
            return forms.CharField(
                widget=forms.Textarea(attrs={'rows': 3}), **common
            )
        return forms.CharField(**common)

    def save(self, commit=True):
        obj = super().save(commit=False)
        specs = dict(obj.specs or {})
        for fname in self.spec_field_names:
            key = fname[len('spec__'):]
            value = self.cleaned_data.get(fname)
            # Convert Decimal/date to string for JSON serialisation
            if value is not None and value != '':
                specs[key] = str(value) if not isinstance(value, (str, bool, int, float)) else value
            else:
                specs[key] = value
        obj.specs = specs
        if commit:
            obj.save()
        return obj


class ConsumableTypeForm(forms.ModelForm):
    class Meta:
        model = ConsumableType
        fields = ['name', 'category', 'description', 'icon']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }
        help_texts = {
            'name': 'Display name for this type',
            'category': 'Broad category',
            'icon': 'Material icon name (e.g. biotech, science)',
        }


class VendorForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = ['name', 'website', 'account_number', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 4}),
        }
        help_texts = {
            'name': 'Supplier or manufacturer name',
            'website': 'Vendor website URL',
            'account_number': 'Your institutional account number with this vendor',
            'notes': 'Any additional notes',
        }


class ConsumableRoomForm(forms.ModelForm):
    class Meta:
        model = ConsumableRoom
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }
        help_texts = {
            'name': 'Room name (e.g. Cold Room, Lab 2)',
        }


class ConsumableLocationForm(forms.ModelForm):
    class Meta:
        model = ConsumableLocation
        fields = ['room', 'name', 'kind', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }
        help_texts = {
            'room': 'Room this location is in',
            'name': 'Location name (e.g. Cabinet B, Shelf 3)',
            'kind': 'Type of storage location',
        }
