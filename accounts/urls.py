from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('login/',  views.login_view,  name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Patients
    path('patients/',              views.patient_list,   name='patient_list'),
    path('patients/add/',          views.patient_add,    name='patient_add'),
    path('patients/<int:pk>/',     views.patient_detail, name='patient_detail'),
    path('patients/<int:pk>/edit/', views.patient_edit,   name='patient_edit'),

    # Users (admin only)
    path('users/',                        views.user_list,          name='user_list'),
    path('users/create/',
         views.user_create,        name='user_create'),
    path('users/<int:pk>/edit/',
         views.user_edit,          name='user_edit'),
    path('users/<int:pk>/toggle-active/',
         views.user_toggle_active, name='user_toggle_active'),

    # Patient portal
    path('portal/',        views.patient_portal,     name='patient_portal'),
    path('portal/report/', views.patient_report_pdf, name='patient_report_pdf'),

    # Child registration (health workers / admin)
    path('patients/register-child/',
         views.child_register,         name='child_register'),
    path('patients/register-child/success/',
         views.child_register_success, name='child_register_success'),
]
