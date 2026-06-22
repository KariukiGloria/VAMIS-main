from django.contrib import admin
from .models import Facility, Supplier, Vaccine, VaccineBatch, StockTransaction, VaccinationRecord, RestockRequest

admin.site.register(Facility)
admin.site.register(Supplier)
admin.site.register(Vaccine)
admin.site.register(VaccineBatch)
admin.site.register(StockTransaction)
admin.site.register(VaccinationRecord)
admin.site.register(RestockRequest)
