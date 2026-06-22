from django.urls import path
from . import views

urlpatterns = [
    path('',              views.alert_list,        name='alert_list'),
    path('<int:pk>/resolve/', views.alert_resolve, name='alert_resolve'),
    path('resolve-all/',  views.alert_resolve_all, name='alert_resolve_all'),
]
