from django.db import models
from django.conf import settings
from django.utils import timezone


class Facility(models.Model):
    FACILITY_TYPES = [
        ('hospital', 'Hospital'),
        ('clinic', 'Clinic'),
        ('dispensary', 'Dispensary'),
        ('health_centre', 'Health Centre'),
    ]
    name = models.CharField(max_length=150)
    location = models.CharField(max_length=100)
    facility_type = models.CharField(max_length=20, choices=FACILITY_TYPES)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)

    class Meta:
        verbose_name_plural = 'Facilities'
        ordering = ['name']

    def __str__(self):
        return self.name


class Supplier(models.Model):
    name = models.CharField(max_length=150)
    contact_email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Vaccine(models.Model):
    ADMIN_METHOD_CHOICES = [
        ('injection', 'Injection'),
        ('oral', 'Oral'),
        ('nasal', 'Nasal Spray'),
    ]
    name = models.CharField(max_length=100)
    target_disease = models.CharField(max_length=100)
    administration_method = models.CharField(
        max_length=20, choices=ADMIN_METHOD_CHOICES)
    required_doses = models.PositiveIntegerField(default=1)
    min_stock_level = models.PositiveIntegerField(
        default=50, help_text='Global minimum stock threshold')
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.target_disease})"

    def current_stock(self, facility=None):
        qs = self.batches.filter(stock_entries__isnull=False)
        if facility:
            total = StockTransaction.objects.filter(
                batch__vaccine=self, facility=facility
            ).aggregate(
                total=models.Sum(
                    models.Case(
                        models.When(transaction_type__in=[
                                    'delivery'], then='quantity_moved'),
                        models.When(transaction_type__in=[
                                    'usage', 'expiry', 'disposal'], then=models.F('quantity_moved') * -1),
                        default=0,
                        output_field=models.IntegerField()
                    )
                )
            )['total'] or 0
        else:
            total = StockTransaction.objects.filter(batch__vaccine=self).aggregate(
                total=models.Sum(
                    models.Case(
                        models.When(transaction_type__in=[
                                    'delivery'], then='quantity_moved'),
                        models.When(transaction_type__in=[
                                    'usage', 'expiry', 'disposal'], then=models.F('quantity_moved') * -1),
                        default=0,
                        output_field=models.IntegerField()
                    )
                )
            )['total'] or 0
        return total


class VaccineBatch(models.Model):
    vaccine = models.ForeignKey(
        Vaccine, on_delete=models.PROTECT, related_name='batches')
    batch_number = models.CharField(max_length=50, unique=True)
    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    expiry_date = models.DateField()
    date_received = models.DateField()
    quantity_received = models.PositiveIntegerField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='batches_created'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_received']
        verbose_name_plural = 'Vaccine Batches'

    def __str__(self):
        return f"{self.vaccine.name} - Batch {self.batch_number}"

    @property
    def is_expired(self):
        return self.expiry_date < timezone.now().date()

    @property
    def days_to_expiry(self):
        delta = self.expiry_date - timezone.now().date()
        return delta.days

    @property
    def is_expiring_soon(self):
        return 0 <= self.days_to_expiry <= settings.EXPIRY_WARNING_DAYS


class StockTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('delivery', 'Delivery'),
        ('distribution', 'Distribution'),
        ('usage', 'Usage/Administration'),
        ('expiry', 'Expiry Disposal'),
        ('disposal', 'Disposal'),
        ('adjustment', 'Stock Adjustment'),
    ]
    batch = models.ForeignKey(
        VaccineBatch, on_delete=models.PROTECT, related_name='stock_entries')
    facility = models.ForeignKey(
        Facility, on_delete=models.PROTECT, related_name='stock_transactions')
    transaction_type = models.CharField(
        max_length=20, choices=TRANSACTION_TYPES)
    quantity_moved = models.PositiveIntegerField()
    transaction_date = models.DateField(default=timezone.now)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='transactions'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-transaction_date', '-created_at']

    def __str__(self):
        return f"{self.transaction_type} - {self.batch.vaccine.name} x{self.quantity_moved}"


class VaccinationRecord(models.Model):
    patient = models.ForeignKey(
        'accounts.Patient', on_delete=models.PROTECT, related_name='vaccinations'
    )
    batch = models.ForeignKey(
        VaccineBatch, on_delete=models.PROTECT, related_name='administrations')
    facility = models.ForeignKey(
        Facility, on_delete=models.PROTECT, related_name='vaccinations')
    administered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='vaccinations_given'
    )
    date_administered = models.DateField(default=timezone.now)
    next_vaccine_date = models.DateField(null=True, blank=True)
    next_vaccine_name = models.CharField(max_length=100, blank=True)
    dose_sequence = models.PositiveIntegerField(default=1)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_administered']

    def __str__(self):
        return f"{self.patient} - {self.batch.vaccine.name} Dose {self.dose_sequence}"


class RestockRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('acknowledged', 'Acknowledged'),
        ('fulfilled', 'Fulfilled'),
        ('cancelled', 'Cancelled'),
    ]
    facility = models.ForeignKey(
        Facility, on_delete=models.PROTECT, related_name='restock_requests')
    vaccine = models.ForeignKey(
        Vaccine, on_delete=models.PROTECT, related_name='restock_requests')
    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='restock_requests_made'
    )
    quantity_needed = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)
    date_requested = models.DateTimeField(auto_now_add=True)
    date_fulfilled = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-date_requested']

    def __str__(self):
        return f"Restock: {self.vaccine.name} x{self.quantity_needed} for {self.facility.name}"
