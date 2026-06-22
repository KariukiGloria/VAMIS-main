from django import forms
from django.utils import timezone
from .models import (Vaccine, VaccineBatch, StockTransaction,
                     VaccinationRecord, RestockRequest, Facility, Supplier)


class FacilityForm(forms.ModelForm):
    class Meta:
        model = Facility
        fields = ['name', 'location', 'facility_type', 'phone', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs['class'] = 'form-control'


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'contact_email', 'phone', 'address']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs['class'] = 'form-control'


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
