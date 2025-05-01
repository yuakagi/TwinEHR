"""Admin for clinical data and related records"""

from django.contrib import admin
from .models import (
    Patients, Admissions, Discharges, Diagnoses, PrescriptionOrders, InjectionOrders, LaboratoryResults
)

# Register your models here.
class ReadOnlyAdmin(admin.ModelAdmin):
    """Base admin class to disable add, change, and delete"""
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
    

class PatientsAdmin(ReadOnlyAdmin):
    """Admin for patient info"""
    list_display = [field.name for field in Patients._meta.fields]

class AdmissionsAdmin(ReadOnlyAdmin):
    """Admin for admission records"""

    list_display = [field.name for field in Admissions._meta.fields]

class DischargesAdmin(ReadOnlyAdmin):
    """Admin for discharge records"""
    list_display = [field.name for field in Discharges._meta.fields]

class DiagnosesAdmin(ReadOnlyAdmin):
    """Admin for diagnoses"""

    list_display = [field.name for field in Diagnoses._meta.fields]


class PrescriptionOrdersAdmin(ReadOnlyAdmin):
    """Admin for prescription orders"""

    list_display = [field.name for field in PrescriptionOrders._meta.fields]


class InjectionOrdersAdmin(ReadOnlyAdmin):
    """Admin for injection orders"""

    list_display = [field.name for field in InjectionOrders._meta.fields]

class LaboratoryResultsAdmin(ReadOnlyAdmin):
    """Admin for laboratory test results"""

    list_display = [field.name for field in LaboratoryResults._meta.fields]


# Register models
for model, admin_class in [
    (Patients, PatientsAdmin),
    (Admissions, AdmissionsAdmin),
    (Discharges, DischargesAdmin),
    (Diagnoses, DiagnosesAdmin),
    (PrescriptionOrders, PrescriptionOrdersAdmin),
    (InjectionOrders, InjectionOrdersAdmin),
    (LaboratoryResults, LaboratoryResultsAdmin),
]:
    admin.site.register(model, admin_class)