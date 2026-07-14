from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator


kenyan_phone_validator = RegexValidator(
    regex=r'^254\d{9}$',
    message='Enter a valid Kenyan phone number starting with 254 followed by 9 digits (e.g. 254712345678).'
)


class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('health_worker', 'Health Worker'),
        ('distributor', 'Distributor'),
        ('patient', 'Patient'),
    ]
    role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default='health_worker')
    facility = models.ForeignKey(
        'inventory.Facility',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='staff'
    )
    phone = models.CharField(
        max_length=20, blank=True,
        validators=[kenyan_phone_validator]
    )
    is_approved = models.BooleanField(default=True)
    must_change_password = models.BooleanField(
        default=False,
        help_text='Force password change on next login (set for auto-generated accounts).'
    )

    # Prevents reverse accessor clash with the built-in auth.User
    groups = models.ManyToManyField(
        'auth.Group',
        blank=True,
        related_name='vamis_users',
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        blank=True,
        related_name='vamis_users',
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_health_worker(self):
        return self.role == 'health_worker'

    @property
    def is_distributor(self):
        return self.role == 'distributor'

    @property
    def is_patient(self):
        return self.role == 'patient'


class Patient(models.Model):
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female'), ('O', 'Other')]
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    phone = models.CharField(
        max_length=20, blank=True,
        validators=[kenyan_phone_validator]
    )
    national_id = models.CharField(
        max_length=20, blank=True, unique=True, null=True)
    guardian_name = models.CharField(max_length=100, blank=True)
    guardian_contact = models.CharField(
        max_length=12,
        blank=True,
        validators=[kenyan_phone_validator],
        help_text='Format: 254XXXXXXXXX (12 digits)'
    )
    user_account = models.OneToOneField(
        'User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='patient_profile'
    )
    facility = models.ForeignKey(
        'inventory.Facility', on_delete=models.SET_NULL,
        null=True, related_name='patients'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self):
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (
                self.date_of_birth.month, self.date_of_birth.day)
        )

    @property
    def age_in_months(self):
        from datetime import date
        today = date.today()
        return (today.year - self.date_of_birth.year) * 12 + (
            today.month - self.date_of_birth.month)

    @property
    def age_display(self):
        months = self.age_in_months
        if months < 1:
            from datetime import date
            days = (date.today() - self.date_of_birth).days
            return f'{days} day{"s" if days != 1 else ""} old'
        if months < 12:
            return f'{months} month{"s" if months != 1 else ""} old'
        years = months // 12
        rem = months % 12
        if rem:
            return f'{years}y {rem}m old'
        return f'{years} year{"s" if years != 1 else ""} old'


class UserPermission(models.Model):
    """
    Granular feature permissions assigned per user by admin.
    Admin always has everything — this model is for health_worker and distributor only.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='permissions_profile'
    )
    # Clinical
    can_view_patients = models.BooleanField(default=True)
    can_register_patients = models.BooleanField(default=True)
    can_record_vaccination = models.BooleanField(default=True)
    # Inventory
    can_view_stock = models.BooleanField(default=True)
    can_manage_stock = models.BooleanField(default=False)
    can_view_batches = models.BooleanField(default=True)
    can_manage_batches = models.BooleanField(default=False)
    can_restock = models.BooleanField(default=True)
    # Alerts
    can_view_alerts = models.BooleanField(default=True)
    can_resolve_alerts = models.BooleanField(default=False)
    # Reports
    can_view_reports = models.BooleanField(default=False)

    def __str__(self):
        return f'Permissions — {self.user}'

    @classmethod
    def get_or_create_for(cls, user):
        """Get or create with role-based defaults."""
        obj, created = cls.objects.get_or_create(user=user)
        if created:
            if user.is_health_worker:
                obj.can_view_patients = True
                obj.can_register_patients = True
                obj.can_record_vaccination = True
                obj.can_view_stock = True
                obj.can_view_batches = True
                obj.can_restock = True
                obj.can_view_alerts = True
                obj.can_resolve_alerts = False
                obj.can_view_reports = False
            elif user.is_distributor:
                obj.can_view_patients = False
                obj.can_register_patients = False
                obj.can_record_vaccination = False
                obj.can_view_stock = True
                obj.can_manage_stock = True
                obj.can_view_batches = True
                obj.can_manage_batches = True
                obj.can_restock = True
                obj.can_view_alerts = False
                obj.can_resolve_alerts = False
                obj.can_view_reports = False
            obj.save()
        return obj
