from django.db import models
from django.conf import settings


class Alert(models.Model):
    ALERT_TYPES = [
        ('low_stock', 'Low Stock'),
        ('expiry_warning', 'Expiry Warning'),
        ('expired', 'Batch Expired'),
        ('restock_fulfilled', 'Restock Fulfilled'),
        ('info', 'Information'),
    ]
    SEVERITY = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('danger', 'Danger'),
    ]
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    severity = models.CharField(
        max_length=10, choices=SEVERITY, default='warning')
    title = models.CharField(max_length=200)
    message = models.TextField()
    vaccine = models.ForeignKey(
        'inventory.Vaccine', on_delete=models.CASCADE,
        null=True, blank=True, related_name='alerts'
    )
    facility = models.ForeignKey(
        'inventory.Facility', on_delete=models.CASCADE,
        null=True, blank=True, related_name='alerts'
    )
    batch = models.ForeignKey(
        'inventory.VaccineBatch', on_delete=models.CASCADE,
        null=True, blank=True, related_name='alerts'
    )
    is_resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='resolved_alerts'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.severity.upper()}] {self.title}"
