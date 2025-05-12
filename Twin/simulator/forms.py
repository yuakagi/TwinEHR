from django import forms
from clinical_records.models import Patients
from accounts.models import UserPatientRelation
from django.utils.translation import gettext_lazy as _
from .models import SimulationRequest


# Form for simulation requests
class SimulationRequestForm(forms.Form):
    patient = forms.ModelChoiceField(
        queryset=Patients.objects.none(),  # Placeholder, will be set in __init__
        label="Patient",
    )
    n_iter = forms.IntegerField(
        label="Number of Iterations", min_value=1, max_value=256, required=True,initial=256
    )
    time_horizon = forms.IntegerField(
        label="Time Horizon (days)", min_value=1, max_value=7, required=True, initial=7
    )
    horizon_start = forms.DateTimeField(
        label="Simulation starts from",
        widget=forms.DateTimeInput(attrs={"id": "horizonStartInput"}),
        required=True,
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)  # Get the user from the form instantiation
        super().__init__(*args, **kwargs)

        # Filter patients based on the active UserPatientRelation for the given user
        if user is not None:
            # Get all patient_ids the user is allowed to see
            allowed_ids = list(
                UserPatientRelation.objects.filter(user=user, is_active=True)
                .values_list("patient_id", flat=True)
            )
            # Filter patients
            self.fields["patient"].queryset = Patients.objects.filter(patient_id__in=allowed_ids)


class SimulationBrowseForm(forms.Form):
    request_id = forms.IntegerField(
        widget=forms.HiddenInput(),
        required=True
    )
    simulation_number = forms.IntegerField(
        label=_("Simulation Number"),
        required=True,
        min_value=0,
        max_value=1000
    )