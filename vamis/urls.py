from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

import accounts

urlpatterns = [
    path('admin/', admin.site.urls),
    path('',        include('core.urls')),
    path('accounts/', include('accounts.urls')),
    path('logout/', accounts.views.logout_view, name='logout'),
    path('inventory/', include('inventory.urls')),
    path('alerts/',    include('alerts.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
