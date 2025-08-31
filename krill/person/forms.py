from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth import get_user_model
from .models import UserRole, Permission, UserPreference, UserAuditLog

User = get_user_model()


class CreateUserForm(UserCreationForm):
    """Form for creating new users with role assignment"""
    role = forms.ChoiceField(
        choices=UserRole.ROLE_CHOICES,
        initial='viewer',
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Select the user role'
    )
    department = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text='Department or organizational unit'
    )
    lab_unit = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text='Specific laboratory unit'
    )
    
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2', 'role', 'department', 'lab_unit')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Style the password fields
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})
    
    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            # Create user role
            UserRole.objects.create(
                user=user,
                role=self.cleaned_data['role'],
                department=self.cleaned_data['department'],
                lab_unit=self.cleaned_data['lab_unit']
            )
            # Create user preference
            UserPreference.objects.create(
                user=user,
                dark_mode=False
            )
        return user


class CustomUserCreationForm(UserCreationForm):
    """Form for creating new users with role assignment"""
    role = forms.ChoiceField(
        choices=UserRole.ROLE_CHOICES,
        initial='viewer',
        help_text='Select the user role'
    )
    department = forms.CharField(
        max_length=100,
        required=False,
        help_text='Department or organizational unit'
    )
    lab_unit = forms.CharField(
        max_length=100,
        required=False,
        help_text='Specific laboratory unit'
    )
    
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 'department', 'lab_unit')
    
    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            # Create user role
            UserRole.objects.create(
                user=user,
                role=self.cleaned_data['role'],
                department=self.cleaned_data['department'],
                lab_unit=self.cleaned_data['lab_unit']
            )
        return user


class CustomUserChangeForm(UserChangeForm):
    """Form for editing existing users"""
    role = forms.ChoiceField(
        choices=UserRole.ROLE_CHOICES,
        required=False,
        help_text='Select the user role'
    )
    department = forms.CharField(
        max_length=100,
        required=False,
        help_text='Department or organizational unit'
    )
    lab_unit = forms.CharField(
        max_length=100,
        required=False,
        help_text='Specific laboratory unit'
    )
    
    class Meta(UserChangeForm.Meta):
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 'department', 'lab_unit')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and hasattr(self.instance, 'role'):
            self.fields['role'].initial = self.instance.role.role
            self.fields['department'].initial = self.instance.role.department
            self.fields['lab_unit'].initial = self.instance.role.lab_unit
    
    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            # Update or create user role
            role, created = UserRole.objects.get_or_create(
                user=user,
                defaults={
                    'role': self.cleaned_data.get('role', 'viewer'),
                    'department': self.cleaned_data.get('department', ''),
                    'lab_unit': self.cleaned_data.get('lab_unit', '')
                }
            )
            if not created:
                role.role = self.cleaned_data.get('role', role.role)
                role.department = self.cleaned_data.get('department', role.department)
                role.lab_unit = self.cleaned_data.get('lab_unit', role.lab_unit)
                role.save()
        return user


class UserRoleForm(forms.ModelForm):
    """Form for managing user roles"""
    class Meta:
        model = UserRole
        fields = ['role', 'department', 'lab_unit']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'lab_unit': forms.TextInput(attrs={'class': 'form-control'}),
        }


class PermissionForm(forms.ModelForm):
    """Form for granting object-level permissions"""
    user = forms.ModelChoiceField(
        queryset=User.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Select the user to grant permission to'
    )
    permission_type = forms.ChoiceField(
        choices=Permission.PERMISSION_TYPES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Type of permission to grant'
    )
    expires_at = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        help_text='Optional expiration date (leave blank for permanent)'
    )
    
    class Meta:
        model = Permission
        fields = ['user', 'permission_type', 'expires_at']
    
    def __init__(self, *args, **kwargs):
        self.content_type = kwargs.pop('content_type', None)
        self.object_id = kwargs.pop('object_id', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True, granted_by=None):
        permission = super().save(commit=False)
        if self.content_type:
            permission.content_type = self.content_type
        if self.object_id:
            permission.object_id = self.object_id
        if granted_by:
            permission.granted_by = granted_by
        
        if commit:
            permission.save()
        return permission


class UserPreferenceForm(forms.ModelForm):
    """Form for user preferences"""
    class Meta:
        model = UserPreference
        fields = ['dark_mode']
        widgets = {
            'dark_mode': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class BulkPermissionForm(forms.Form):
    """Form for bulk permission operations"""
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        help_text='Select users to grant permissions to'
    )
    permission_type = forms.ChoiceField(
        choices=Permission.PERMISSION_TYPES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Type of permission to grant'
    )
    expires_at = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        help_text='Optional expiration date (leave blank for permanent)'
    )


class UserSearchForm(forms.Form):
    """Form for searching users"""
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by username, email, or name...'
        })
    )
    role = forms.ChoiceField(
        choices=[('', 'All Roles')] + UserRole.ROLE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    department = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filter by department...'
        })
    )
    is_active = forms.ChoiceField(
        choices=[('', 'All Users'), ('True', 'Active Only'), ('False', 'Inactive Only')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class AuditLogFilterForm(forms.Form):
    """Form for filtering audit logs"""
    user = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    action = forms.ChoiceField(
        choices=[('', 'All Actions')] + UserAuditLog.ACTION_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    target_type = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filter by target type...'
        })
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
