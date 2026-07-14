from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.db import transaction
from .forms import LoginForm, UserCreateForm, UserEditForm, PatientForm, ChildRegistrationForm, GuardianContactForm
from .models import User, Patient
from inventory.models import (VaccinationRecord, StockTransaction,
                              Facility, Vaccine, VaccineBatch, RestockRequest)
from alerts.models import Alert
from .decorators import permission_required

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from django.http import HttpResponse

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from django.http import HttpResponse


# ─── AUTH ─────────────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_patient:
            return redirect('patient_portal')
        return redirect('dashboard')
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        messages.success(
            request, f'Welcome back, {user.first_name or user.username}!')
        if user.is_patient:
            return redirect('patient_portal')
        next_url = request.GET.get('next', 'dashboard')
        return redirect(next_url)
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('login')


# ─── DASHBOARD ────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    import datetime
    from django.utils import timezone
    user = request.user
    context = {'user': user}

    if user.is_admin:
        expiring_soon = VaccineBatch.objects.filter(
            expiry_date__lte=timezone.now().date() + datetime.timedelta(days=30),
            expiry_date__gte=timezone.now().date()
        ).select_related('vaccine').order_by('expiry_date')

        context.update({
            'total_vaccines': Vaccine.objects.count(),
            'total_facilities': Facility.objects.count(),
            'total_users': User.objects.count(),
            'total_patients': Patient.objects.count(),
            'pending_restocks': RestockRequest.objects.filter(status='pending').count(),
            'unresolved_alerts': Alert.objects.filter(is_resolved=False).count(),
            'recent_transactions': StockTransaction.objects.select_related(
                'batch__vaccine', 'facility', 'performed_by'
            ).order_by('-created_at')[:8],
            'expiring_batches': expiring_soon[:6],
            'alerts': Alert.objects.filter(is_resolved=False).order_by('-created_at')[:8],
            'recent_vaccinations': VaccinationRecord.objects.select_related(
                'patient', 'batch__vaccine', 'facility'
            ).order_by('-date_administered')[:5],
        })

    elif user.is_health_worker:
        facility = user.facility
        recent_vacc = []
        facility_alerts = []
        if facility:
            recent_vacc = VaccinationRecord.objects.filter(
                facility=facility
            ).select_related('patient', 'batch__vaccine').order_by('-date_administered')[:10]
            facility_alerts = Alert.objects.filter(
                facility=facility, is_resolved=False
            ).order_by('-created_at')[:5]

        context.update({
            'facility': facility,
            'recent_vaccinations': recent_vacc,
            'alerts': facility_alerts,
            'today_count': VaccinationRecord.objects.filter(
                facility=facility,
                date_administered=datetime.date.today()
            ).count() if facility else 0,
            'pending_restocks': RestockRequest.objects.filter(
                facility=facility, status='pending'
            ).count() if facility else 0,
        })

    elif user.is_distributor:
        context.update({
            'pending_requests': RestockRequest.objects.filter(
                status='pending'
            ).select_related('vaccine', 'facility', 'requested_by').order_by('-date_requested')[:10],
            'acknowledged_requests': RestockRequest.objects.filter(
                status='acknowledged'
            ).select_related('vaccine', 'facility')[:5],
            'recent_batches': user.batches_created.select_related(
                'vaccine', 'supplier'
            ).order_by('-created_at')[:8],
            'total_delivered': user.batches_created.count(),
        })

    return render(request, 'accounts/dashboard.html', context)


# ─── PATIENTS ─────────────────────────────────────────────────────────────────

@login_required
@permission_required('can_view_patients')
def patient_list(request):
    if request.user.is_distributor:
        messages.error(request, 'You do not have access to patient records.')
        return redirect('dashboard')
    query = request.GET.get('q', '').strip()
    patients = Patient.objects.select_related(
        'facility').order_by('last_name', 'first_name')
    if not request.user.is_admin and request.user.facility:
        patients = patients.filter(facility=request.user.facility)
    if query:
        patients = patients.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(national_id__icontains=query) |
            Q(phone__icontains=query) |
            Q(guardian_name__icontains=query)
        )
    return render(request, 'accounts/patients.html', {
        'patients': patients,
        'query': query,
        'total': patients.count(),
    })


@login_required
def patient_detail(request, pk):
    if request.user.is_distributor:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    patient = get_object_or_404(Patient, pk=pk)
    vaccinations = VaccinationRecord.objects.filter(
        patient=patient
    ).select_related('batch__vaccine', 'facility', 'administered_by').order_by('-date_administered')
    return render(request, 'accounts/patient_detail.html', {
        'patient': patient,
        'vaccinations': vaccinations,
    })


@login_required
@permission_required('can_register_patients')
def patient_add(request):
    if request.user.is_distributor:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    # All patient registration goes through child_register
    # which collects guardian details and creates a login account
    return redirect('child_register')


@login_required
def patient_edit(request, pk):
    if request.user.is_distributor:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    patient = get_object_or_404(Patient, pk=pk)
    form = PatientForm(request.POST or None, instance=patient)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'{patient.full_name} updated successfully.')
        return redirect('patient_detail', pk=patient.pk)
    return render(request, 'accounts/patient_form.html', {
        'form': form, 'title': f'Edit — {patient.full_name}',
        'action': 'Save Changes', 'patient': patient
    })


# ─── USERS ────────────────────────────────────────────────────────────────────

@login_required
def user_list(request):
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    users = User.objects.select_related(
        'facility').order_by('role', 'last_name')
    role_filter = request.GET.get('role', '')
    if role_filter:
        users = users.filter(role=role_filter)
    return render(request, 'accounts/users.html', {
        'users': users,
        'role_filter': role_filter,
        'role_choices': User.ROLE_CHOICES,
    })


@login_required
def user_create(request):
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    form = UserCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        messages.success(
            request, f'User {user.get_full_name()} created successfully.')
        return redirect('user_list')
    return render(request, 'accounts/user_form.html', {
        'form': form, 'title': 'Create New User', 'action': 'Create User'
    })


@login_required
def user_edit(request, pk):
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    user_obj = get_object_or_404(User, pk=pk)
    form = UserEditForm(request.POST or None, instance=user_obj)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(
            request, f'{user_obj.get_full_name()} updated successfully.')
        return redirect('user_list')
    return render(request, 'accounts/user_form.html', {
        'form': form, 'title': f'Edit — {user_obj.get_full_name()}',
        'action': 'Save Changes', 'edit_user': user_obj
    })


@login_required
def user_toggle_active(request, pk):
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    if request.user.pk == pk:
        messages.error(request, 'You cannot deactivate your own account.')
        return redirect('user_list')
    user_obj = get_object_or_404(User, pk=pk)
    user_obj.is_active = not user_obj.is_active
    user_obj.save()
    state = 'activated' if user_obj.is_active else 'deactivated'
    messages.success(request, f'{user_obj.get_full_name()} has been {state}.')
    return redirect('user_list')


@login_required
def user_permissions_edit(request, pk):
    if not request.user.is_admin:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    from .models import UserPermission
    from .forms import UserPermissionForm
    user_obj = get_object_or_404(User, pk=pk)
    # Admins and patients don't need granular permissions
    if user_obj.is_admin or user_obj.is_patient:
        messages.warning(
            request,
            'Permissions are only configurable for health workers and distributors.'
        )
        return redirect('user_list')
    perms = UserPermission.get_or_create_for(user_obj)
    form = UserPermissionForm(request.POST or None, instance=perms)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(
            request, f'Permissions updated for {user_obj.get_full_name()}.')
        return redirect('user_list')
    return render(request, 'accounts/user_permissions.html', {
        'form': form,
        'target_user': user_obj,
    })

# ─── PATIENT PORTAL ───────────────────────────────────────────────────────────


@login_required
def patient_portal(request):
    if not request.user.is_patient:
        return redirect('dashboard')
   # Force password change on first login
    if request.user.must_change_password:
        return redirect('patient_change_password')

   # Safety net — atomic registration prevents this, but handles edge cases

    # Safety net — atomic registration prevents this, but handles edge cases
    try:
        patient = request.user.patient_profile
    except Patient.DoesNotExist:
        return render(request, 'accounts/portal_error.html', status=400)

    from datetime import date
    today = date.today()

    vaccinations = VaccinationRecord.objects.filter(
        patient=patient
    ).select_related('batch__vaccine', 'facility', 'administered_by').order_by('-date_administered')

    # Upcoming reminders with days_until annotated
    reminders_qs = VaccinationRecord.objects.filter(
        patient=patient,
        next_vaccine_date__gte=today
    ).select_related('batch__vaccine', 'facility').order_by('next_vaccine_date')

    reminder_list = []
    for r in reminders_qs:
        r.days_until = (r.next_vaccine_date - today).days
        reminder_list.append(r)

    next_due = reminder_list[0] if reminder_list else None

    contact_form = GuardianContactForm(instance=patient)
    if request.method == 'POST' and 'update_contact' in request.POST:
        contact_form = GuardianContactForm(request.POST, instance=patient)
        if contact_form.is_valid():
            contact_form.save()
            # Sync to the linked User account's phone field (admin sees this)
            if patient.user_account:
                patient.user_account.phone = patient.guardian_contact
                patient.user_account.save(update_fields=['phone'])
            messages.success(request, 'Contact number updated successfully.')
            return redirect('patient_portal')

    return render(request, 'accounts/patient_portal.html', {
        'patient': patient,
        'vaccinations': vaccinations,
        'reminder_list': reminder_list,
        'next_due': next_due,
        'contact_form': contact_form,
        'today': today,
    })


# ─── CHILD REGISTRATION (health worker) ────────────────────────────────────────

@login_required
@permission_required('can_register_patients')
def child_register(request):
    if not (request.user.is_health_worker or request.user.is_admin):
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    form = ChildRegistrationForm(
        request.POST or None, health_worker=request.user)

    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                patient = form.save(commit=False)
                patient.gender = 'O'

                # Generate unique username + secure password
                username, raw_password = ChildRegistrationForm.generate_credentials(
                    patient.guardian_name)

                # Create the patient User — inside the same transaction
                patient_user = User.objects.create_user(
                    username=username,
                    password=raw_password,
                    first_name=patient.guardian_name,
                    phone=patient.guardian_contact,
                    role='patient',
                    must_change_password=True,
                )
                patient.user_account = patient_user
                patient.save()
                # Both patient and user_account saved — or both rolled back

            # Store credentials in session, shown ONCE then cleared
                request.session['new_patient_credentials'] = {
                    'patient_name': patient.full_name,
                    'guardian_name': patient.guardian_name,
                    'username': username,
                    'password': raw_password,
                }
            request.session['new_patient_credentials'] = {
                'patient_name': patient.full_name,
                'guardian_name': patient.guardian_name,
                'username': username,
                'password': raw_password,
            }
            return redirect('child_register_success')

        except Exception as e:
            messages.error(
                request, f'Registration failed. Please try again. ({e})')

    return render(request, 'accounts/child_register.html', {
        'form': form,
        'title': 'Register Child',
    })


@login_required
def child_register_success(request):
    if not (request.user.is_health_worker or request.user.is_admin):
        return redirect('dashboard')
    credentials = request.session.pop('new_patient_credentials', None)
    if not credentials:
        messages.warning(request, 'No recent registration found.')
        return redirect('patient_list')
    return render(request, 'accounts/child_register_success.html', {
        'credentials': credentials,
    })


@login_required
def patient_report_pdf(request):
    """Printable vaccination history for the logged-in patient (browser print → PDF)."""
    if not request.user.is_patient:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    try:
        patient = request.user.patient_profile
    except Patient.DoesNotExist:
        return render(request, 'accounts/portal_error.html', status=400)

    from datetime import date
    vaccinations = VaccinationRecord.objects.filter(
        patient=patient
    ).select_related('batch__vaccine', 'facility', 'administered_by').order_by('date_administered')

    return render(request, 'accounts/patient_report_print.html', {
        'patient': patient,
        'vaccinations': vaccinations,
        'generated': date.today(),
    })


# ─── PATIENT PASSWORD CHANGE ──────────────────────────────────────────────────

@login_required
def patient_change_password(request):
    if not request.user.is_patient:
        return redirect('dashboard')

    from .forms import PatientPasswordChangeForm
    form = PatientPasswordChangeForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        new_password = form.cleaned_data['new_password1']
        request.user.set_password(new_password)
        request.user.must_change_password = False
        request.user.save()
        update_session_auth_hash(request, request.user)
        messages.success(request, 'Password changed successfully. Welcome!')
        return redirect('patient_portal')

    return render(request, 'accounts/patient_change_password.html', {
        'form': form,
        'forced': request.user.must_change_password,
    })
