from datetime import date
from alerts.models import Alert


def global_context(request):
    context = {}
    if not request.user.is_authenticated:
        return context

    if request.user.role == 'patient':
        try:
            patient = request.user.patient_profile
            from inventory.models import VaccinationRecord
            today = date.today()
            reminders_qs = VaccinationRecord.objects.filter(
                patient=patient,
                next_vaccine_date__gte=today
            ).select_related('batch__vaccine', 'facility').order_by('next_vaccine_date')

            reminders = []
            for r in reminders_qs:
                delta = (r.next_vaccine_date - today).days
                r.days_until = delta
                r.urgency = 'urgent' if delta <= 3 else 'upcoming'
                reminders.append(r)
            context['patient_reminders'] = reminders
        except Exception:
            context['patient_reminders'] = []
        return context

    unresolved = Alert.objects.filter(is_resolved=False)
    if hasattr(request.user, 'facility') and request.user.facility and not request.user.is_admin:
        unresolved = unresolved.filter(facility=request.user.facility)
    context['unread_alerts_count'] = unresolved.count()
    context['recent_alerts'] = unresolved[:5]
    return context
