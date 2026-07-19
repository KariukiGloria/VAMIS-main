from django.urls import path
from . import views

urlpatterns = [
    # Facilities
    path('facilities/',              views.facility_list, name='facility_list'),
    path('facilities/add/',          views.facility_add,  name='facility_add'),
    path('facilities/<int:pk>/edit/', views.facility_edit, name='facility_edit'),

    # Suppliers
    path('suppliers/',          views.supplier_list,      name='supplier_list'),
    path('suppliers/add/',      views.supplier_add,       name='supplier_add'),
    path('suppliers/create/',   views.supplier_create,    name='supplier_create'),
    path('distributor/',        views.distributor_portal,
         name='distributor_portal'),

    # Vaccines
    path('vaccines/',              views.vaccine_list,   name='vaccine_list'),
    path('vaccines/add/',          views.vaccine_add,    name='vaccine_add'),
    path('vaccines/<int:pk>/',     views.vaccine_detail, name='vaccine_detail'),
    path('vaccines/<int:pk>/edit/', views.vaccine_edit,   name='vaccine_edit'),

    # Batches
    path('batches/',     views.batch_list, name='batch_list'),
    path('batches/add/', views.batch_add,  name='batch_add'),

    # Stock
    path('stock/',     views.stock_list, name='stock_list'),
    path('stock/add/', views.stock_add,  name='stock_add'),

    # Vaccinations
    path('vaccinations/',     views.vaccination_list, name='vaccination_list'),
    path('vaccinations/add/', views.vaccination_add,  name='vaccination_add'),

    # Restock requests
    path('restocks/',                       views.restock_list,
         name='restock_list'),
    path('restocks/add/',
         views.restock_add,           name='restock_add'),
    path('restocks/<int:pk>/status/',
         views.restock_update_status, name='restock_update_status'),

    # Reports
    path('reports/', views.reports, name='reports'),
]
