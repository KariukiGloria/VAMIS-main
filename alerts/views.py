from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Alert
from accounts.decorators import permission_required


@login_required
@permission_required('can_view_alerts')
def alert_list(request):
    qs = Alert.objects.select_related(
        'vaccine', 'facility', 'batch', 'resolved_by')
    if not request.user.is_admin and request.user.facility:
        qs = qs.filter(facility=request.user.facility)
    severity_filter = request.GET.get('severity', '')
    if severity_filter:
        qs = qs.filter(severity=severity_filter)
    unresolved = qs.filter(is_resolved=False).order_by('-created_at')
    resolved = qs.filter(is_resolved=True).order_by('-resolved_at')[:30]
    return render(request, 'alerts/list.html', {
        'unresolved': unresolved,
        'resolved': resolved,
        'severity_filter': severity_filter,
    })


@login_required
@permission_required('can_resolve_alerts')
def alert_resolve(request, pk):
    alert = get_object_or_404(Alert, pk=pk)
    alert.is_resolved = True
    alert.resolved_by = request.user
    alert.resolved_at = timezone.now()
    alert.save()
    messages.success(request, f'Alert "{alert.title}" marked as resolved.')
    return redirect('alert_list')


@login_required
@permission_required('can_resolve_alerts')
def alert_resolve_all(request):
    qs = Alert.objects.filter(is_resolved=False)
    if not request.user.is_admin and request.user.facility:
        qs = qs.filter(facility=request.user.facility)
    count = qs.count()
    qs.update(is_resolved=True, resolved_by=request.user,
              resolved_at=timezone.now())
    messages.success(request, f'{count} alert(s) resolved.')
    return redirect('alert_list')
