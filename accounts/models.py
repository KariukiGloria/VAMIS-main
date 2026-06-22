from django.contrib.auth.models import AbstractUser
from django.db import models


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
    phone = models.CharField(max_length=20, blank=True)
    is_approved = models.BooleanField(default=True)

    # Required when using a custom user model alongside AbstractUser
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
    phone = models.CharField(max_length=20, blank=True)
    national_id = models.CharField(
        max_length=20, blank=True, unique=True, null=True)
    guardian_name = models.CharField(max_length=100, blank=True)
    guardian_contact = models.CharField(max_length=20, blank=True)
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