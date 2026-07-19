from django import forms
from django.utils import timezone
import re
from .models import (Vaccine, VaccineBatch, StockTransaction,
                     VaccinationRecord, RestockRequest, Facility, Supplier)


# ── Shared validators ──────────────────────────────────────────────────────────

def validate_kenyan_phone(value):
    cleaned = re.sub(r'[\s\-]', '', value.strip())
    if not re.fullmatch(r'^254\d{9}$', cleaned):
        raise forms.ValidationError(
            'Enter a valid Kenyan number: 254 followed by exactly 9 digits '
            '(e.g. 254712345678).'
        )
    return cleaned


def validate_positive_integer(value):
    if value is not None and value <= 0:
        raise forms.ValidationError('This value must be greater than zero.')
    return value


class FacilityForm(forms.ModelForm):
    class Meta:
        model = Facility
        fields = ['name', 'location', 'facility_type', 'phone', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs['class'] = 'form-control'
        self.fields['phone'].widget.attrs['placeholder'] = '254712345678'

    def clean_phone(self):
        val = self.cleaned_data.get('phone', '').strip()
        if val:
            return validate_kenyan_phone(val)
        return val

    def clean_name(self):
        val = self.cleaned_data.get('name', '').strip()
        if not val:
            raise forms.ValidationError('Facility name is required.')
        if re.search(r'[^A-Za-z0-9\s\'\-\.\,\&]', val):
            raise forms.ValidationError(
                'Facility name contains invalid characters.')
        return val


class SupplierForm(forms.ModelForm):
    """Used for editing an existing supplier record (no account creation)."""
    class Meta:
        model = Supplier
        fields = ['name', 'contact_email', 'phone', 'address']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs['class'] = 'form-control'
        self.fields['phone'].widget.attrs['placeholder'] = '254712345678'

    def clean_phone(self):
        val = self.cleaned_data.get('phone', '').strip()
        if val:
            return validate_kenyan_phone(val)
        return val

    def clean_name(self):
        val = self.cleaned_data.get('name', '').strip()
        if not re.fullmatch(r"^[A-Za-z0-9\s'\-\.\,\&]+$", val):
            raise forms.ValidationError(
                'Supplier name contains invalid characters.')
        return val


class SupplierCreateForm(forms.Form):
    """
    Admin creates a supplier AND their login account in one step.
    The distributor logs in with these credentials and sees their portal.
    """
    # Supplier details
    name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'Company / supplier name'})
    )
    contact_email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={'class': 'form-control', 'placeholder': 'supplier@email.com'})
    )
    phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': '254712345678'})
    )
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
                              'class': 'form-control', 'rows': 2, 'placeholder': 'Physical address (optional)'})
    )
    # Login account details
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'Login username for this supplier'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={'class': 'form-control', 'placeholder': 'Set a password'})
    )
    password2 = forms.CharField(
        label='Confirm password',
        widget=forms.PasswordInput(
            attrs={'class': 'form-control', 'placeholder': 'Repeat password'})
    )

    def clean_name(self):
        val = self.cleaned_data.get('name', '').strip()
        if not re.fullmatch(r"^[A-Za-z0-9\s'\-\.\,\&]+$", val):
            raise forms.ValidationError(
                'Supplier name contains invalid characters.')
        return val

    def clean_phone(self):
        return validate_kenyan_phone(self.cleaned_data.get('phone', ''))

    def clean_username(self):
        from accounts.models import User
        username = self.cleaned_data.get('username', '').strip()
        if not re.fullmatch(r'^[A-Za-z0-9_\-\.]+$', username):
            raise forms.ValidationError(
                'Username may only contain letters, numbers, underscores, hyphens and dots.')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('This username is already taken.')
        return username

    def clean_password(self):
        pw = self.cleaned_data.get('password', '')
        if len(pw) < 8:
            raise forms.ValidationError(
                'Password must be at least 8 characters.')
        if not re.search(r'[A-Za-z]', pw):
            raise forms.ValidationError(
                'Password must contain at least one letter.')
        if not re.search(r'[0-9]', pw):
            raise forms.ValidationError(
                'Password must contain at least one number.')
        return pw

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned


class VaccineForm(forms.ModelForm):
    class Meta:
        model = Vaccine
        fields = ['name', 'target_disease', 'administration_method',
                  'required_doses', 'min_stock_level', 'description']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs['class'] = 'form-control'
        self.fields['description'].widget.attrs['rows'] = 3

    def clean_name(self):
        val = self.cleaned_data.get('name', '').strip()
        if not re.fullmatch(r"^[A-Za-z0-9\s\(\)\-\/\.]+$", val):
            raise forms.ValidationError(
                'Vaccine name contains invalid characters.')
        return val

    def clean_required_doses(self):
        val = self.cleaned_data.get('required_doses')
        if val is not None and val < 1:
            raise forms.ValidationError('Required doses must be at least 1.')
        if val is not None and val > 10:
            raise forms.ValidationError('Required doses cannot exceed 10.')
        return val

    def clean_min_stock_level(self):
        val = self.cleaned_data.get('min_stock_level')
        if val is not None and val < 0:
            raise forms.ValidationError(
                'Minimum stock level cannot be negative.')
        return val


class VaccineBatchForm(forms.ModelForm):
    expiry_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    date_received = forms.DateField(
        widget=forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control'}),
        initial=timezone.now
    )

    class Meta:
        model = VaccineBatch
        fields = ['vaccine', 'batch_number', 'supplier', 'expiry_date',
                  'date_received', 'quantity_received', 'notes']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, f in self.fields.items():
            if name not in ('expiry_date', 'date_received'):
                f.widget.attrs['class'] = 'form-control'
        self.fields['notes'].widget.attrs['rows'] = 2
        self.fields['notes'].required = False

    def clean_batch_number(self):
        val = self.cleaned_data.get('batch_number', '').strip()
        if not re.fullmatch(r'^[A-Za-z0-9\-\_\/]+$', val):
            raise forms.ValidationError(
                'Batch number may only contain letters, numbers, hyphens, underscores and slashes.')
        return val.upper()

    def clean_quantity_received(self):
        val = self.cleaned_data.get('quantity_received')
        if val is not None and val <= 0:
            raise forms.ValidationError(
                'Quantity received must be greater than zero.')
        if val is not None and val > 100000:
            raise forms.ValidationError(
                'Quantity seems unrealistically high. Please check.')
        return val

    def clean(self):
        cleaned = super().clean()
        exp = cleaned.get('expiry_date')
        rec = cleaned.get('date_received')
        if exp and rec and exp <= rec:
            raise forms.ValidationError(
                'Expiry date must be after the date received.')
        return cleaned


class StockTransactionForm(forms.ModelForm):
    transaction_date = forms.DateField(
        widget=forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control'}),
        initial=timezone.now
    )

    class Meta:
        model = StockTransaction
        fields = ['batch', 'facility', 'transaction_type',
                  'quantity_moved', 'transaction_date', 'notes']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        for name, f in self.fields.items():
            if name != 'transaction_date':
                f.widget.attrs['class'] = 'form-control'
        self.fields['notes'].widget.attrs['rows'] = 2
        self.fields['notes'].required = False
        # Scope facility to user's own facility for non-admins
        if user and not user.is_admin and user.facility:
            self.fields['facility'].queryset = Facility.objects.filter(
                pk=user.facility.pk)
            self.fields['facility'].initial = user.facility

    def clean_quantity_moved(self):
        val = self.cleaned_data.get('quantity_moved')
        if val is not None and val <= 0:
            raise forms.ValidationError('Quantity must be greater than zero.')
        if val is not None and val > 100000:
            raise forms.ValidationError(
                'Quantity seems unrealistically high. Please check.')
        return val


class VaccinationRecordForm(forms.ModelForm):
    date_administered = forms.DateField(
        widget=forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control'}),
        initial=timezone.now
    )
    next_vaccine_date = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control'}),
        help_text='Leave blank if no follow-up needed'
    )

    class Meta:
        model = VaccinationRecord
        fields = ['patient', 'batch', 'facility', 'date_administered',
                  'dose_sequence', 'next_vaccine_name', 'next_vaccine_date', 'notes']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        for name, f in self.fields.items():
            if name != 'date_administered':
                f.widget.attrs['class'] = 'form-control'
        self.fields['notes'].widget.attrs['rows'] = 2
        self.fields['notes'].required = False
        if user and not user.is_admin and user.facility:
            self.fields['facility'].queryset = Facility.objects.filter(
                pk=user.facility.pk)
            self.fields['facility'].initial = user.facility
            from accounts.models import Patient
            self.fields['patient'].queryset = Patient.objects.filter(
                facility=user.facility)
        # Only show non-expired batches
        from django.utils import timezone as tz
        self.fields['batch'].queryset = VaccineBatch.objects.filter(
            expiry_date__gte=tz.now().date()
        ).select_related('vaccine').order_by('vaccine__name')

    def clean_dose_sequence(self):
        dose = self.cleaned_data.get('dose_sequence')
        batch = self.cleaned_data.get('batch')
        if batch and dose and dose > batch.vaccine.required_doses:
            raise forms.ValidationError(
                f'{batch.vaccine.name} only requires {batch.vaccine.required_doses} dose(s).'
            )
        return dose


class RestockRequestForm(forms.ModelForm):
    class Meta:
        model = RestockRequest
        fields = ['facility', 'vaccine',
                  'supplier', 'quantity_needed', 'notes']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs['class'] = 'form-control'
        self.fields['notes'].widget.attrs['rows'] = 3
        self.fields['notes'].required = False
        self.fields['supplier'].required = False
        if user and not user.is_admin and user.facility:
            self.fields['facility'].queryset = Facility.objects.filter(
                pk=user.facility.pk)
            self.fields['facility'].initial = user.facility

    def clean_quantity_needed(self):
        val = self.cleaned_data.get('quantity_needed')
        if val is not None and val <= 0:
            raise forms.ValidationError(
                'Quantity needed must be greater than zero.')
        if val is not None and val > 100000:
            raise forms.ValidationError(
                'Quantity seems unrealistically high. Please check.')
        return val
