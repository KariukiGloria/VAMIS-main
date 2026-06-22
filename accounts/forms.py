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
    """Simplified form for health workers registering a child under 2 yrs."""
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
            self.fields['facility'].widget.attrs['class'] = 'form-control'

    def save(self, commit=True):
        patient = super().save(commit=False)
        patient.gender = 'O'
        if commit:
            patient.save()
        return patient


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
