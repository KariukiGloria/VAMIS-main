import re
import secrets
import string
from datetime import date

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, UserChangeForm
from django.core.validators import RegexValidator
from .models import User, Patient, UserPermission


# ── Shared validators ──────────────────────────────────────────────────────────

kenyan_phone_validator = RegexValidator(
    regex=r'^254\d{9}$',
    message='Enter a valid Kenyan number: 254 followed by 9 digits (e.g. 254712345678).'
)

name_validator = RegexValidator(
    regex=r'^[A-Za-z\s\'\-]+$',
    message='Name may only contain letters, spaces, hyphens and apostrophes.'
)


# ── Auth ───────────────────────────────────────────────────────────────────────

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Username',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Password',
        })
    )


class UserCreateForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email',
                  'phone', 'role', 'facility', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['email'].required = True


class UserEditForm(UserChangeForm):
    password = None

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email',
                  'phone', 'role', 'facility', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


# ── Patient (general / admin edit) ────────────────────────────────────────────

class PatientForm(forms.ModelForm):
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    class Meta:
        model = Patient
        fields = [
            'first_name', 'last_name', 'date_of_birth', 'gender',
            'national_id', 'guardian_name', 'guardian_contact', 'facility',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != 'date_of_birth':
                field.widget.attrs['class'] = 'form-control'
        self.fields['national_id'].required = False
        self.fields['guardian_name'].required = True
        self.fields['guardian_contact'].required = True
        self.fields['guardian_contact'].widget.attrs['placeholder'] = '254712345678'

    def clean_national_id(self):
        nid = self.cleaned_data.get('national_id') or None
        if nid:
            qs = Patient.objects.filter(national_id=nid)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    'A patient with this National ID already exists.')
        return nid

    def clean_guardian_contact(self):
        value = self.cleaned_data.get('guardian_contact', '').strip()
        value = re.sub(r'[\s\-]', '', value)
        if not re.fullmatch(r'^254\d{9}$', value):
            raise forms.ValidationError(
                'Enter a valid Kenyan number: 254 followed by exactly 9 digits '
                '(e.g. 254712345678).'
            )
        qs = Patient.objects.filter(guardian_contact=value)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(
                'This contact number is already linked to another child record.')
        return value


# ── Child registration (health worker) ────────────────────────────────────────

class ChildRegistrationForm(forms.ModelForm):

    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    class Meta:
        model = Patient
        fields = [
            'first_name', 'last_name', 'date_of_birth', 'gender',
            'guardian_name', 'guardian_contact', 'facility',
        ]

    def __init__(self, *args, **kwargs):
        self.health_worker = kwargs.pop('health_worker', None)
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != 'date_of_birth':
                field.widget.attrs['class'] = 'form-control'

        # Placeholders
        self.fields['first_name'].widget.attrs['placeholder'] = "Child's first name"
        self.fields['last_name'].widget.attrs['placeholder'] = "Child's last name"
        self.fields['guardian_name'].widget.attrs['placeholder'] = 'Full name of parent/guardian'
        self.fields['guardian_contact'].widget.attrs['placeholder'] = '254712345678'

        # Required fields
        self.fields['guardian_name'].required = True
        self.fields['guardian_contact'].required = True
        self.fields['gender'].required = True

        # Pre-fill facility from health worker's assigned facility
        if self.health_worker and self.health_worker.facility:
            self.fields['facility'].initial = self.health_worker.facility
            self.fields['facility'].widget.attrs['class'] = 'form-control'

    def save(self, commit=True):
        patient = super().save(commit=False)
        patient.gender = 'O'
        if commit:
            patient.save()
        return patient


class GuardianContactForm(forms.ModelForm):
    """Allows the guardian/patient-user to update their contact number from the portal."""

    class Meta:
        model = Patient
        fields = ['guardian_contact']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['guardian_contact'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '254712345678',
        })
        self.fields['guardian_contact'].required = True

    def clean_guardian_contact(self):
        value = self.cleaned_data.get('guardian_contact', '').strip()
        value = re.sub(r'[\s\-]', '', value)
        if not re.fullmatch(r'^254\d{9}$', value):
            raise forms.ValidationError(
                'Enter a valid Kenyan number: 254 followed by exactly 9 digits '
                '(e.g. 254712345678). No spaces or dashes.'
            )
        # Exclude current patient when checking uniqueness
        qs = Patient.objects.filter(guardian_contact=value)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(
                'This contact number is already linked to another child record.'
            )
        return value


class PatientPasswordChangeForm(forms.Form):
    """Used by patients/guardians to change their auto-generated password."""
    new_password1 = forms.CharField(
        label='New password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password',
            'autofocus': True,
        })
    )
    new_password2 = forms.CharField(
        label='Confirm new password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Repeat new password',
        })
    )

    def clean_new_password1(self):
        password = self.cleaned_data.get('new_password1', '')
        if len(password) < 8:
            raise forms.ValidationError(
                'Password must be at least 8 characters.')
        if not re.search(r'[A-Za-z]', password):
            raise forms.ValidationError(
                'Password must contain at least one letter.')
        if not re.search(r'[0-9]', password):
            raise forms.ValidationError(
                'Password must contain at least one number.')
        return password

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('new_password1')
        p2 = cleaned_data.get('new_password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned_data


class UserPermissionForm(forms.ModelForm):
    class Meta:
        model = UserPermission
        exclude = ['user']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-check-input'
            # Make label human-readable
            field.label = name.replace('can_', '').replace('_', ' ').title()
