from django.urls import path
from .views import (
    ajax_code_autocomplete,
    search_patients,
    PatientHomeView,
    patients_admissions,
    patients_diagnoses,
    patients_prescription_orders,
    patients_injection_orders,
    patients_laboratory_results,
    patients_lab_chart,
)

urlpatterns = [
    # Autocomplete for medical codes (for select2)
    path("code-autocomplete/<str:code_type>/", ajax_code_autocomplete, name="patients_code_autocomplete"),
    # Patient search
    path("find_patients/", search_patients, name="patients_find_patients"),
    # Patient home page
    path("<str:pk>/home/", PatientHomeView.as_view(), name="patients_home"),
    # Display admission and discharge records
    path(
        "<str:pk>/admissions/",
        patients_admissions,
        name="patients_admissions",
    ),
    # Display diagnosis records
    path(
        "<str:pk>/diagnoses/",
        patients_diagnoses,
        name="patients_diagnoses",
    ),
    # Display prescription orders
    path(
        "<str:pk>/prescription_orders/",
        patients_prescription_orders,
        name="patients_prescription_orders",
    ),
    # Display injection orders
    path(
        "<str:pk>/injection_orders/",
        patients_injection_orders,
        name="patients_injection_orders",
    ),
    # Display laboratory test results
    path(
        "<str:pk>/laboratory_results/",
        patients_laboratory_results,
        name="patients_laboratory_results",
    ),
    # Display laboratory test result chart
    path(
        "<str:pk>/lab_chart/<str:item_code>/", patients_lab_chart, name="patients_lab_chart"
    ),
]
