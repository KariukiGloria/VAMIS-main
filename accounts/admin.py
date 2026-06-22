from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Patient


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'role', 'facility', 'is_active']
    list_filter = ['role', 'is_active']
    fieldsets = UserAdmin.fieldsets + (
        ('VAMIS', {'fields': ('role', 'facility', 'phone')}),
    )

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'date_of_birth', 'gender', 'facility', 'phone']
    search_fields = ['first_name', 'last_name', 'national_id']
    list_filter = ['gender', 'facility']
    
    
