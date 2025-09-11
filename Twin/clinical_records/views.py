"""Views related to patients and clinical records"""

from typing import Any, Literal
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
import pandas as pd
from django.utils.translation import gettext_lazy as _
from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.functions import Coalesce
from django.views.generic import DetailView
from django.db.models import Model, Value, Q, OuterRef, Subquery
from django.http import HttpRequest, HttpResponse, JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from accounts.models import UserPatientRelation, CustomUser
from .forms import PatientSearchForm, ClinicalRecordSelectionForm, RelationEditForm
from .models import (
    DiagnosisCodes,
    MedicationCodes,
    LabTestCodes,
    Patients,
    Admissions,
    Discharges,
    Diagnoses,
    PrescriptionOrders,
    InjectionOrders,
    LaboratoryResults,
)
from twin_utils import is_ajax
import config


def _get_patient_base_contexts(patient: Patients, user: CustomUser) -> dict:
    """Return common context for patient pages."""
    # Calculate age
    delta = relativedelta(datetime.now(), patient.date_of_birth)
    if delta.years >= 1:
        age_str = f"{delta.years} year{'s' if delta.years > 1 else ''} old"
    elif delta.months >= 1:
        age_str = f"{delta.months} month{'s' if delta.months > 1 else ''} old"
    else:
        age_str = f"{delta.days} day{'s' if delta.days != 1 else ''} old"

    # Patient-user relation
    try:
        relation = UserPatientRelation.objects.get(
            patient_id=patient.patient_id, user=user
        )
        following = relation.is_active
    except UserPatientRelation.DoesNotExist:
        relation = None
        following = False

    return {
        "age": age_str,
        "following": following,
        "relation": relation,
        "relation_edit_form": RelationEditForm(instance=relation),
    }


# AJAX request for code candidates
@login_required
@ratelimit(key="user", rate="60/m", method="GET", block=True)
def ajax_code_autocomplete(request, code_type: Literal["dx", "med", "lab"]):
    model_dict = {"dx": DiagnosisCodes, "med": MedicationCodes, "lab": LabTestCodes}
    if code_type not in model_dict:
        return JsonResponse({"results": []}, status=400)

    model = model_dict[code_type]
    query = request.GET.get("q", "").strip()
    results = []

    if query:
        keywords = query.split()
        q_object = Q()
        for kw in keywords:
            # NOTE: Consider using |= for logical or for less strict search
            q_object &= Q(item_name__icontains=kw) | Q(item_code__icontains=kw)

        qs = model.objects.filter(q_object)[:20]
        results = [
            {"id": obj.item_code, "text": f"{obj.item_code} – {obj.item_name}"}
            for obj in qs
        ]

    return JsonResponse({"results": results})


@login_required
@csrf_protect
@ratelimit(key="ip", rate="10/m", method="POST", block=True)
def search_patients(request: HttpRequest, n_max=1000) -> HttpResponse:
    form = PatientSearchForm(request.POST or None)
    patient_list = Patients.objects.none()
    today = date.today()
    msgs = []

    
    if request.method == "POST":
        if form.is_valid():

            cd = form.cleaned_data
            base_query = Q()

            if cd.get("patient_id"):
                base_query &= Q(patient_id__icontains=cd["patient_id"])
            if cd.get("first_name"):
                base_query &= Q(first_name__icontains=cd["first_name"])
            if cd.get("last_name"):
                base_query &= Q(last_name__icontains=cd["last_name"])
            if cd.get("sex"):
                base_query &= Q(sex=cd["sex"])
            if cd.get("min_age"):
                min_age = int(cd["min_age"])
                base_query &= Q(
                    date_of_birth__lte=(today - relativedelta(years=min_age))
                )
            if cd.get("max_age"):
                max_age = int(cd["max_age"])
                base_query &= Q(
                    date_of_birth__gte=(today - relativedelta(years=max_age))
                )

            patient_list = Patients.objects.filter(base_query).distinct()

            # If codes are present, refine patient_list using intersection logic
            if any([cd.get("dx_code"), cd.get("med_code"), cd.get("lab_code")]):
                start = cd["search_start"]
                end = cd["search_end"]
                code_ids = None  # Start with None, intersect as needed
                code_map = {
                    "dx_code": (Diagnoses, "item_code"),
                    "med_code": (PrescriptionOrders, "item_code"),
                    "lab_code": (LaboratoryResults, "item_code"),
                }

                for key, (model, code_field) in code_map.items():
                    code_val = cd.get(key)
                    if code_val:
                        ids = set(
                            model.objects.filter(
                                **{f"{code_field}__icontains": code_val},
                                timestamp__range=[start, end],
                            ).values_list("patient_id", flat=True)[:n_max]
                        )
                        code_ids = ids if code_ids is None else code_ids & ids

                # Final filter
                if code_ids:
                    patient_list = patient_list.filter(patient_id__in=code_ids)
                else:
                    patient_list = Patients.objects.none()

            # Cap to n_max
            patient_list = patient_list.order_by("-patient_id")[:n_max]

            if not patient_list.exists():
                msgs.append("No patients found.")

        else:
            msgs.append("Form error. Check your inputs.")
            msgs += list(form.errors.values())
            render(
                request,
                "patient/patient_search.html",
                {"form": form, "patient_list": patient_list, "messages": msgs},
            )

    return render(
        request,
        "patient/patient_search.html",
        {"form": form, "patient_list": patient_list, "messages": msgs},
    )


@method_decorator(
    ratelimit(key="user", rate="20/m", method="GET", block=True), name="dispatch"
)
class PatientHomeView(LoginRequiredMixin, DetailView):
    """Render the patient home page."""

    model = Patients
    template_name = "patient/patient_home.html"
    context_object_name = "patient"

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        patient = context["patient"]
        user = self.request.user

        # Single relation object
        relationship = UserPatientRelation.objects.filter(
            patient_id=patient.patient_id, user=user
        ).first()

        # Extend context
        common_context = _get_patient_base_contexts(patient, user)
        context["relationship"] = relationship
        context.update(common_context)
        return context


@login_required
@csrf_protect
@ratelimit(key="user", rate="20/m", method=["GET", "POST"], block=True)
def display_patient_records(
    request: HttpRequest,
    pk: str,
    template_name: str,
    model: Model,
    allow_all: bool = False,
    default_period: int = 1,
    max_shown: int = 1000,
) -> HttpResponse | JsonResponse:
    """Displays clinical records.

    Args:
        request (HttpRequest): HTTP request.
        pk (str): Primary key assigned to the target patient.
        template_name (str): Template name.
        model (Model): Target record model.
        allow_all (bool): If True, allows selecting "All Records".
        default_period (int): Default number of days to search.
        max_shown (int): Maximum records to return.

    Returns:
        HttpResponse | JsonResponse: JSON response if AJAX, otherwise an HTML response.
    """
    ajax = is_ajax(request)
    patient = get_object_or_404(Patients, pk=pk)
    msgs = []

    # ***** Handle GET request *****
    if request.method == "GET":
        # Fetch unique timestamps
        unique_dates = (
            model.objects.filter(patient=patient)
            .exclude(timestamp=None)
            .dates("timestamp", "day", order="DESC")
        )
        # Extract unique dates
        if unique_dates:
            unique_dates = (
                pd.to_datetime(pd.Series(unique_dates))
                .dt.strftime(config.PG_DATE_FORMAT)
                .tolist()
            )
        else:
            unique_dates = []
        if not unique_dates:
            form = None
            selected_date_str = None
            selected_period = None
        else:
            form = ClinicalRecordSelectionForm(
                dates=unique_dates, allow_all=allow_all, initial_period=default_period
            )
            selected_date_str = form.fields["date_selection"].initial
            selected_period = form.fields["period"].initial

    # ***** Handle POST request *****
    elif request.method == "POST":
        # Create form
        # NOTE: The default choices are empty, therefore, you need dates=[selected_date_raw]... part
        selected_date_raw = request.POST.get("date_selection")
        form = ClinicalRecordSelectionForm(
            data=request.POST,
            dates=[selected_date_raw] if selected_date_raw else [],
            )
        if form.is_valid():
            selected_date_str = form.cleaned_data["date_selection"]
            selected_period = form.cleaned_data["period"]
        else:
            if ajax:
                msgs.append("Invalid form submission.")
                return JsonResponse(
                    {
                        "records": [],
                        "messages": msgs,
                        "form_errors": {
                            field: list(errors) for field, errors in form.errors.items()
                        },
                    },
                    safe=False,
                    status=400,
                )  # Return 400 Bad Request for invalid input
            else:
                return HttpResponseBadRequest("Invalid form submission.")

    # ***** Query *****
    if selected_date_str and selected_period:
        # Set query params
        code_map_models = {
            LaboratoryResults: LabTestCodes,
            Diagnoses: DiagnosisCodes,
            PrescriptionOrders: MedicationCodes,
            InjectionOrders: MedicationCodes,
        }
        map_model = code_map_models.get(model)
        if not map_model:
            raise ValueError("Cannot find the model for code mapping")
        if selected_date_str == "all":
            filter_kwargs = dict(patient=patient)
        else:
            search_start = datetime.strptime(selected_date_str, config.PG_DATE_FORMAT)
            search_end = search_start + timedelta(days=selected_period)
            filter_kwargs = dict(
                patient=patient, timestamp__range=[search_start, search_end]
            )
        # Query with code mapping
        records_qs = (
            model.objects.filter(**filter_kwargs)
            .annotate(
                item_name=Coalesce(
                    Subquery(
                        map_model.objects.filter(
                            item_code=OuterRef(config.COL_ITEM_CODE)
                        ).values(config.COL_ITEM_NAME)[:1]
                    ),
                    Value("(no data)"),  # Default if no mapping found
                )
            )
            .order_by("-timestamp")[: max_shown + 1]  # Limit at DB level
        )
        # Convert QuerySet into a list of dictionaries (each dictionary as a record)
        records = list(records_qs.values())

        # Handle excess records
        if len(records) > max_shown:
            msgs.append(
                f"More than {max_shown} records found. Displaying only {max_shown}."
            )
            records = records[:max_shown]
    else:
        records = []
    # Return JSON if AJAX
    if ajax:
        if records:
            return JsonResponse(
                {"records": records, "messages": msgs}, safe=False, status=200
            )
        # Return error if no record was found
        else:
            msgs.append("No records found for this patient.")
            return JsonResponse(
                {"records": [], "messages": msgs},
                safe=False,
                status=200,
            )

    # Render template with updated context
    common_context = _get_patient_base_contexts(patient, request.user)
    return render(
        request,
        template_name,
        {
            "patient": patient,
            "records": records,
            "record_form": form,
            "messages": msgs,
            **common_context,
        },
    )


def patients_laboratory_results(
    request: HttpRequest, pk: str
) -> HttpResponse | JsonResponse:
    """Displays injection orders"""
    return display_patient_records(
        request,
        pk,
        template_name="patient/patient_laboratory_results.html",
        model=LaboratoryResults,
        default_period=1,
    )


def patients_prescription_orders(
    request: HttpRequest, pk: str
) -> HttpResponse | JsonResponse:
    """Displays prescription orders"""
    return display_patient_records(
        request,
        pk,
        template_name="patient/patient_prescription_orders.html",
        model=PrescriptionOrders,
        default_period=30,
    )


def patients_injection_orders(
    request: HttpRequest, pk: str
) -> HttpResponse | JsonResponse:
    """Displays injection orders"""
    return display_patient_records(
        request,
        pk,
        template_name="patient/patient_injection_orders.html",
        model=InjectionOrders,
        default_period=30,
    )


def patients_diagnoses(request: HttpRequest, pk: str) -> HttpResponse | JsonResponse:
    """Displays diagnosis records."""
    return display_patient_records(
        request,
        pk,
        template_name="patient/patient_diagnoses.html",
        model=Diagnoses,
        default_period=180,
    )


@login_required
@csrf_protect
@ratelimit(key="user", rate="20/m", method="GET", block=True)
def patients_admissions(request: HttpRequest, pk: str) -> HttpResponse:
    """Displays admission and discharge records.

    Args:
        request (HttpRequest): HTTP request.
        pk (str): Primary key assigned to the target patient.
    Returns:
        HttpResponse: Renders a HTML template.
    """
    # Get the specific patient or return 404
    patient = get_object_or_404(Patients, pk=pk)

    # Query
    admissions = list(
        Admissions.objects.filter(patient=patient)
        .exclude(timestamp__isnull=True)
        .order_by("timestamp")
    )
    discharges = list(
        Discharges.objects.filter(patient=patient)
        .exclude(timestamp__isnull=True)
        .order_by("timestamp")
    )

    # Ensure admissions and discharges are correctly matched
    hospital_stays = []
    admission_iter = iter(admissions)
    discharge_iter = iter(discharges)

    try:
        while True:
            admission = next(admission_iter)
            # Get the next discharge that occurs **after** the admission
            discharge = next(
                (d for d in discharge_iter if d.timestamp >= admission.timestamp),
                None,  # If no valid discharge is found, use None
            )
            hospital_stays.append((admission, discharge))
    except StopIteration:
        pass

    common_context = _get_patient_base_contexts(patient, request.user)
    return render(
        request,
        "patient/patient_admissions.html",
        {
            "patient": patient,
            "records": hospital_stays,
            **common_context,
        },
    )


@login_required
@csrf_protect
@ratelimit(key="user", rate="20/m", method="GET", block=True)
def patients_lab_chart(request: HttpRequest, pk: str, item_code: str) -> HttpResponse:
    """Displays lab test results as a time-series chart.

    Args:
        request (HttpRequest): HTTP request.
        pk (str): Primary key of the patient.
        item_code (str): Lab test code.

    Returns:
        HttpResponse: Renders the time-series chart page.
    """

    # NOTE: This only supports for numeric results.
    # TODO (Yu Akagi): Implement visualization pages for non-numeric test results too.

    # Get patient & lab results
    patient = get_object_or_404(Patients, pk=pk)
    lab_results = (
        LaboratoryResults.objects.filter(
            patient=patient,
            item_code=item_code,
            numeric__isnull=False,
            timestamp__isnull=False,
        )
        .only("numeric", "timestamp", "unit")
        .order_by("timestamp")[:100]
    )  # <- Reversed order

    # Clean data
    data = []
    units = []
    item_code = lab_results[0].item_code if lab_results else "(no label)"
    lab_code_map = LabTestCodes.objects.filter(item_code=item_code).first()
    item_name = lab_code_map.item_name if lab_code_map else item_code
    for result in lab_results:
        x = result.timestamp.strftime(config.PG_DATETIME_FORMAT)
        y = float(result.numeric)
        data.append({"x": x, "y": y})
        units.append(result.unit)
    # Render the page
    common_context = _get_patient_base_contexts(patient, request.user)
    return render(
        request,
        "patient/patient_lab_chart.html",
        {
            "patient": patient,
            "item_name": item_name,
            "data_dict": data,
            "units": units,
            **common_context,
        },
    )
