from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Case, When, F, IntegerField, Count
from django.utils import timezone
import datetime

from .models import (Vaccine, VaccineBatch, StockTransaction,
                     VaccinationRecord, RestockRequest, Facility, Supplier)
from .forms import (FacilityForm, SupplierForm, VaccineForm, VaccineBatchForm,
                    StockTransactionForm, VaccinationRecordForm, RestockRequestForm)
from alerts.models import Alert
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from inventory.models import VaccinationRecord


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _stock_balance(vaccine, facility):
    return StockTransaction.objects.filter(
        batch__vaccine=vaccine, facility=facility
    ).aggregate(
        total=Sum(Case(
            When(transaction_type='delivery', then='quantity_moved'),
            When(transaction_type__in=['usage', 'expiry', 'disposal'], then=F(
                'quantity_moved') * -1),
            default=0, output_field=IntegerField()
        ))
    )['total'] or 0


def check_and_create_alerts(vaccine, facility):
    stock = _stock_balance(vaccine, facility)
    if stock < vaccine.min_stock_level:
        Alert.objects.get_or_create(
            alert_type='low_stock', vaccine=vaccine,
            facility=facility, is_resolved=False,
            defaults={
                'severity': 'danger',
                'title': f'Low Stock: {vaccine.name}',
                'message': (
                    f'{vaccine.name} at {facility.name} is {stock} units '
                    f'(minimum: {vaccine.min_stock_level}).'
                ),
            }
        )
    # Check for expiry
    expiring = VaccineBatch.objects.filter(
        vaccine=vaccine,
        expiry_date__lte=timezone.now().date() + datetime.timedelta(days=30),
        expiry_date__gte=timezone.now().date()
    )
    for batch in expiring:
        Alert.objects.get_or_create(
            alert_type='expiry_warning', batch=batch,
            facility=facility, is_resolved=False,
            defaults={
                'severity': 'warning',
                'title': f'Expiry Warning: {vaccine.name}',
                'message': (
                    f'Batch {batch.batch_number} expires in '
                    f'{batch.days_to_expiry} day(s). Use these first.'
                ),
                'vaccine': vaccine,
            }
        )


# ─── FACILITIES ───────────────────────────────────────────────────────────────

@login_required
def facility_list(request):
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    facilities = Facility.objects.annotate(
        staff_count=Count('staff'),
        patient_count=Count('patients')
    ).order_by('name')
    return render(request, 'inventory/facilities.html', {'facilities': facilities})


@login_required
def facility_add(request):
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('facility_list')
    form = FacilityForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        facility = form.save()
        messages.success(request, f'Facility "{facility.name}" added.')
        return redirect('facility_list')
    return render(request, 'inventory/facility_form.html', {
        'form': form, 'title': 'Add Facility'
    })


@login_required
def facility_edit(request, pk):
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('facility_list')
    facility = get_object_or_404(Facility, pk=pk)
    form = FacilityForm(request.POST or None, instance=facility)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Facility "{facility.name}" updated.')
        return redirect('facility_list')
    return render(request, 'inventory/facility_form.html', {
        'form': form, 'title': f'Edit — {facility.name}', 'facility': facility
    })


# ─── SUPPLIERS ────────────────────────────────────────────────────────────────

@login_required
def supplier_list(request):
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    suppliers = Supplier.objects.all().order_by('name')
    return render(request, 'inventory/suppliers.html', {'suppliers': suppliers})


@login_required
def supplier_add(request):
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('supplier_list')
    form = SupplierForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        supplier = form.save()
        messages.success(request, f'Supplier "{supplier.name}" added.')
        return redirect('supplier_list')
    return render(request, 'inventory/supplier_form.html', {
        'form': form, 'title': 'Add Supplier'
    })


# ─── VACCINES ─────────────────────────────────────────────────────────────────

@login_required
def vaccine_list(request):
    query = request.GET.get('q', '').strip()
    vaccines = Vaccine.objects.all().order_by('name')
    if query:
        vaccines = vaccines.filter(
            Q(name__icontains=query) | Q(target_disease__icontains=query)
        )
    return render(request, 'inventory/vaccines.html', {
        'vaccines': vaccines, 'query': query
    })


@login_required
def vaccine_detail(request, pk):
    vaccine = get_object_or_404(Vaccine, pk=pk)
    batches = VaccineBatch.objects.filter(
        vaccine=vaccine
    ).select_related('supplier').order_by('-date_received')
    return render(request, 'inventory/vaccine_detail.html', {
        'vaccine': vaccine,
        'batches': batches,
    })


@login_required
def vaccine_add(request):
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('vaccine_list')
    form = VaccineForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        vaccine = form.save()
        messages.success(
            request, f'Vaccine "{vaccine.name}" added to catalogue.')
        return redirect('vaccine_detail', pk=vaccine.pk)
    return render(request, 'inventory/vaccine_form.html', {
        'form': form, 'title': 'Add Vaccine'
    })


@login_required
def vaccine_edit(request, pk):
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('vaccine_list')
    vaccine = get_object_or_404(Vaccine, pk=pk)
    form = VaccineForm(request.POST or None, instance=vaccine)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Vaccine "{vaccine.name}" updated.')
        return redirect('vaccine_detail', pk=vaccine.pk)
    return render(request, 'inventory/vaccine_form.html', {
        'form': form, 'title': f'Edit — {vaccine.name}', 'vaccine': vaccine
    })


# ─── BATCHES ──────────────────────────────────────────────────────────────────

@login_required
def batch_list(request):
    batches = VaccineBatch.objects.select_related(
        'vaccine', 'supplier', 'created_by'
    ).order_by('-date_received')
    query = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    if query:
        batches = batches.filter(
            Q(batch_number__icontains=query) | Q(
                vaccine__name__icontains=query)
        )
    if status == 'expired':
        batches = [b for b in batches if b.is_expired]
    elif status == 'expiring':
        batches = [b for b in batches if b.is_expiring_soon]
    elif status == 'good':
        batches = [
            b for b in batches if not b.is_expired and not b.is_expiring_soon]
    return render(request, 'inventory/batches.html', {
        'batches': batches, 'query': query, 'status': status
    })


@login_required
def batch_add(request):
    if not (request.user.is_admin or request.user.is_distributor):
        messages.error(request, 'Access denied.')
        return redirect('batch_list')
    form = VaccineBatchForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        batch = form.save(commit=False)
        batch.created_by = request.user
        batch.save()
        messages.success(
            request, f'Batch {batch.batch_number} recorded successfully.')
        return redirect('batch_list')
    return render(request, 'inventory/batch_form.html', {
        'form': form, 'title': 'Log New Vaccine Batch'
    })


# ─── STOCK ────────────────────────────────────────────────────────────────────

@login_required
def stock_list(request):
    txns = StockTransaction.objects.select_related(
        'batch__vaccine', 'facility', 'performed_by'
    ).order_by('-transaction_date', '-created_at')
    if not request.user.is_admin and request.user.facility:
        txns = txns.filter(facility=request.user.facility)
    type_filter = request.GET.get('type', '')
    if type_filter:
        txns = txns.filter(transaction_type=type_filter)
    return render(request, 'inventory/stock.html', {
        'transactions': txns,
        'type_filter': type_filter,
        'transaction_types': StockTransaction.TRANSACTION_TYPES,
    })


@login_required
def stock_add(request):
    form = StockTransactionForm(request.POST or None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        txn = form.save(commit=False)
        txn.performed_by = request.user
        txn.save()
        check_and_create_alerts(txn.batch.vaccine, txn.facility)
        messages.success(request, 'Stock transaction recorded.')
        return redirect('stock_list')
    return render(request, 'inventory/stock_form.html', {
        'form': form, 'title': 'Record Stock Transaction'
    })


# ─── VACCINATIONS ─────────────────────────────────────────────────────────────

@login_required
def vaccination_list(request):
    if request.user.is_distributor:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    records = VaccinationRecord.objects.select_related(
        'patient', 'batch__vaccine', 'facility', 'administered_by'
    ).order_by('-date_administered')
    if not request.user.is_admin and request.user.facility:
        records = records.filter(facility=request.user.facility)
    query = request.GET.get('q', '').strip()
    if query:
        records = records.filter(
            Q(patient__first_name__icontains=query) |
            Q(patient__last_name__icontains=query) |
            Q(batch__vaccine__name__icontains=query)
        )
    return render(request, 'inventory/vaccinations.html', {
        'records': records, 'query': query
    })


@login_required
def vaccination_add(request):
    if request.user.is_distributor:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    # Pre-select patient from query param
    initial = {}
    patient_pk = request.GET.get('patient')
    if patient_pk:
        initial['patient'] = patient_pk
    form = VaccinationRecordForm(
        request.POST or None, user=request.user, initial=initial
    )
    if request.method == 'POST' and form.is_valid():
        record = form.save(commit=False)
        record.administered_by = request.user
        record.save()
        # Auto-create stock usage transaction
        StockTransaction.objects.create(
            batch=record.batch,
            facility=record.facility,
            transaction_type='usage',
            quantity_moved=1,
            transaction_date=record.date_administered,
            performed_by=request.user,
            notes=f'Auto-recorded: vaccination of {record.patient.full_name}'
        )
        check_and_create_alerts(record.batch.vaccine, record.facility)
        messages.success(
            request, f'Vaccination recorded for {record.patient.full_name}.')
        return redirect('patient_detail', pk=record.patient.pk)
    return render(request, 'inventory/vaccination_form.html', {
        'form': form, 'title': 'Record Vaccination'
    })


# ─── RESTOCK REQUESTS ─────────────────────────────────────────────────────────

@login_required
def restock_list(request):
    qs = RestockRequest.objects.select_related(
        'vaccine', 'facility', 'requested_by', 'supplier'
    ).order_by('-date_requested')
    if request.user.is_health_worker and request.user.facility:
        qs = qs.filter(facility=request.user.facility)
    status_filter = request.GET.get('status', '')
    if status_filter:
        qs = qs.filter(status=status_filter)
    return render(request, 'inventory/restocks.html', {
        'requests': qs,
        'status_filter': status_filter,
        'status_choices': RestockRequest.STATUS_CHOICES,
    })


@login_required
def restock_add(request):
    if request.user.is_distributor:
        messages.error(request, 'Access denied.')
        return redirect('restock_list')
    form = RestockRequestForm(request.POST or None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        req = form.save(commit=False)
        req.requested_by = request.user
        req.save()
        messages.success(request, 'Restock request submitted successfully.')
        return redirect('restock_list')
    return render(request, 'inventory/restock_form.html', {
        'form': form, 'title': 'New Restock Request'
    })


@login_required
def restock_update_status(request, pk):
    req = get_object_or_404(RestockRequest, pk=pk)
    new_status = request.POST.get('status')
    valid = [s[0] for s in RestockRequest.STATUS_CHOICES]
    if new_status not in valid:
        messages.error(request, 'Invalid status.')
        return redirect('restock_list')
    if not (request.user.is_admin or request.user.is_distributor):
        messages.error(request, 'Access denied.')
        return redirect('restock_list')
    req.status = new_status
    if new_status == 'fulfilled':
        req.date_fulfilled = timezone.now()
        Alert.objects.create(
            alert_type='restock_fulfilled',
            severity='info',
            title=f'Restock Fulfilled: {req.vaccine.name}',
            message=(
                f'{req.quantity_needed} units of {req.vaccine.name} '
                f'fulfilled for {req.facility.name}.'
            ),
            vaccine=req.vaccine,
            facility=req.facility,
        )
    req.save()
    messages.success(
        request, f'Request #{pk} updated to "{req.get_status_display()}".')
    return redirect('restock_list')


# ─── REPORTS ──────────────────────────────────────────────────────────────────

@login_required
def reports(request):
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    from django.db.models.functions import TruncMonth
    # Vaccinations per month (last 6 months)
    six_months_ago = timezone.now().date() - datetime.timedelta(days=180)
    monthly_vacc = (
        VaccinationRecord.objects
        .filter(date_administered__gte=six_months_ago)
        .annotate(month=TruncMonth('date_administered'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    # Stock per vaccine
    vaccine_stock = []
    for v in Vaccine.objects.all():
        total = StockTransaction.objects.filter(batch__vaccine=v).aggregate(
            bal=Sum(Case(
                When(transaction_type='delivery', then='quantity_moved'),
                When(transaction_type__in=['usage', 'expiry', 'disposal'],
                     then=F('quantity_moved') * -1),
                default=0, output_field=IntegerField()
            ))
        )['bal'] or 0
        vaccine_stock.append({'vaccine': v, 'stock': total})

    context = {
        'monthly_vacc': list(monthly_vacc),
        'vaccine_stock': vaccine_stock,
    })


@login_required
def patient_report_pdf(request):
    return HttpResponse("Patient PDF report will be implemented here.")
