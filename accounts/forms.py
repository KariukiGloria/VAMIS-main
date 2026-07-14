import re
import secrets
import string
from datetime import date

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, UserChangeForm
from .models import User, Patient


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
    password = None  # hide raw password field

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email',
                  'phone', 'role', 'facility', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class PatientForm(forms.ModelForm):
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    class Meta:
        model = Patient
        fields = ['first_name', 'last_name', 'date_of_birth', 'gender',
                  'phone', 'national_id', 'guardian_name', 'facility']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != 'date_of_birth':
                field.widget.attrs['class'] = 'form-control'
        self.fields['national_id'].required = False
        self.fields['guardian_name'].required = False
        self.fields['phone'].required = False

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


class ChildRegistrationForm(forms.ModelForm):
    """Health worker registers a child (patient). Age must be under 5 years."""
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    class Meta:
        model = Patient
        fields = ['first_name', 'last_name', 'date_of_birth',
                  'guardian_name', 'guardian_contact', 'facility']

    def __init__(self, *args, **kwargs):
        self.health_worker = kwargs.pop('health_worker', None)
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != 'date_of_birth':
                field.widget.attrs['class'] = 'form-control'
        self.fields['guardian_name'].required = True
        self.fields['guardian_contact'].required = True
        if self.health_worker and self.health_worker.facility:
            self.fields['facility'].initial = self.health_worker.facility

    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob:
            today = date.today()
            if dob > today:
                raise forms.ValidationError(
                    'Date of birth cannot be in the future.')
            age_months = (today.year - dob.year) * \
                12 + (today.month - dob.month)
            if age_months > 60:
                raise forms.ValidationError(
                    'This system only manages children under 5 years old.')
        return dob

    @staticmethod
    def generate_credentials(guardian_name):
        """Generate a unique username (from guardian name) and a secure password."""
        base = re.sub(
            r'[^a-z0-9]', '', guardian_name.lower().replace(' ', ''))[:12] or 'patient'
        username = base
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f'{base}{counter}'
            counter += 1
        alphabet = string.ascii_letters + string.digits
        raw_password = ''.join(secrets.choice(alphabet) for _ in range(10))
        return username, raw_password


class GuardianContactForm(forms.ModelForm):
    """Allows the guardian/patient-user to update their contact number."""
    class Meta:
        model = Patient
        fields = ['guardian_contact']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['guardian_contact'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '+254 7XX XXX XXX',
        })
        self.fields['guardian_contact'].required = True
