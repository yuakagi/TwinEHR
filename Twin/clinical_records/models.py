"""Models for clinical records.
These models are not managed by Django itself.
You can create model templates by 'manage.py inspectdb <table>'.
"""

from django.db import models


# Medical codes
class MedicationCodes(models.Model):
    item_code = models.CharField(primary_key=True, max_length=200)
    item_name = models.CharField(max_length=200)

    class Meta:
        managed = False
        db_table = 'medication_codes'

class DiagnosisCodes(models.Model):
    item_code = models.CharField(primary_key=True, max_length=200)
    item_name = models.CharField(max_length=200)

    class Meta:
        managed = False
        db_table = 'diagnosis_codes'

class LabTestCodes(models.Model):
    item_code = models.CharField(primary_key=True, max_length=200)
    item_name = models.CharField(max_length=200)

    class Meta:
        managed = False
        db_table = 'lab_test_codes'


# Patient
class Patients(models.Model):
    
    unique_record_id = models.TextField(primary_key=True)
    patient_id = models.CharField(unique=True, max_length=200)
    sex = models.CharField(max_length=1)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    date_of_birth = models.DateField()

    class Meta:
        managed = False
        db_table = 'patients'

    def __str__(self):
        return f"{self.last_name} {self.first_name} ({self.patient_id})"

# Clinical records
class Admissions(models.Model):
    
    unique_record_id = models.TextField(primary_key=True)
    patient = models.ForeignKey('Patients', models.DO_NOTHING, to_field='patient_id')
    timestamp = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'admissions'

class Discharges(models.Model):
    
    unique_record_id = models.TextField(primary_key=True)
    patient = models.ForeignKey('Patients', models.DO_NOTHING, to_field='patient_id')
    timestamp = models.DateTimeField(blank=True, null=True)
    disposition = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'discharges'


class Diagnoses(models.Model):
    
    unique_record_id = models.TextField(primary_key=True)
    patient = models.ForeignKey('Patients', models.DO_NOTHING, to_field='patient_id')
    timestamp = models.DateTimeField(blank=True, null=True)
    item_code = models.CharField(max_length=200, blank=True, null=True)
    provisional = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'diagnoses'

class PrescriptionOrders(models.Model):
    
    unique_record_id = models.TextField(primary_key=True)
    patient = models.ForeignKey(Patients, models.DO_NOTHING, to_field='patient_id')
    timestamp = models.DateTimeField(blank=True, null=True)
    item_code = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'prescription_orders'

class InjectionOrders(models.Model):
    
    unique_record_id = models.TextField(primary_key=True)
    patient = models.ForeignKey('Patients', models.DO_NOTHING, to_field='patient_id')
    timestamp = models.DateTimeField(blank=True, null=True)
    item_code = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'injection_orders'

class LaboratoryResults(models.Model):
    
    unique_record_id = models.TextField(primary_key=True)
    patient = models.ForeignKey('Patients', models.DO_NOTHING, to_field='patient_id')
    timestamp = models.DateTimeField(blank=True, null=True)
    time_available = models.DateTimeField(blank=True, null=True)
    item_code = models.CharField(max_length=200, blank=True, null=True)
    numeric = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)
    unit = models.CharField(max_length=20, blank=True, null=True)
    nonnumeric = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'laboratory_results'

