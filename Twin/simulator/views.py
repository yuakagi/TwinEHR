import requests
import logging
import re
from datetime import datetime
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.safestring import mark_safe
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_protect
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import config
from clinical_records.models import Patients
from .forms import SimulationRequestForm, SimulationBrowseForm
from .models import SimulationRequest, SimulationResult


logger = logging.getLogger(__name__)

# ==============
# Const
# ==============
# region Simulation Const
# HTML template for a timeline item
TL_TEMPLATE = """
<li class="list-unstyled mb-4">

  <!-- sticky time bar -->
  <div class="d-inline-flex align-items-center gap-2 sticky-top
              px-3 py-1 rounded-3 shadow-sm"
       style="background-color:{color}; top:0;">
    <i class="{icon} text-white" style="font-size:1.25rem;"></i>
    <span class="text-white small fw-semibold">{time}</span>
  </div>

  <!-- content block -->
  <div class="ms-4 mt-2">
    <h6 class="mb-1">{title}</h6>
    <p class="mb-0 text-muted">{descr}</p>
  </div>

</li>
"""


RECORD_TYPE_COLORS = {
    1: "#5799d2",  # Admission
    2: "#5799d2",  # Discharge
    3: "#f49945",  # Dx
    4: "#62b346",  # Medication
    5: "#62b346",  # Medication
    6: "#de6866",  # Lab test
    7: "#6f7c91",  # End of timeline
}

RECORD_TYPE_ICONS = {
    1: "bi-door-closed",  # Admission
    2: "bi-door-open",  # Discharge
    3: "bi-pencil-square",  # Dx
    4: "bi-prescription",  # Medication
    5: "bi-prescription",  # Medication
    6: "bi-eyedropper",  # Lab test
    7: "bi-check-circle-fill",  # End of timeline
}

RECORD_TYPE_LABELS = {
    1: "Admission",
    2: "Discharge",
    3: "Diagnosis",
    4: "Medication Order",
    5: "Medication Order",
    6: "Laboratory Test Result",
    7: "End of Followup",
}

DISCHARGE_RESULT_DICT = {
    "[DSC_ALV]": "Alive",
    "[DSC_EXP]": "Died",
}

BROAD_ABX = [
            "Vancomycin",
            "Linezolid",
            "Daptomycin",
            "heparin",
            "electrolytes"
        ]

LAB_CODES = {
    "serum_sodium": {"keywords":["serum", "sodium", "quantitative"], "units":["mmol/L", "mEq/L", "meq/L"]},
    # Potassium
    "serum_potassium": {"keywords":["serum", "potassium", "quantitative"], "units":["mmol/L", "mEq/L", "meq/L"]},

}

# endregion


# ==============
# Utils
# ==============
# region Simulation Utils
def _extract_numeric_from_text(col: pd.Series) -> pd.Series:
    """Extracts numeric values from texts.
    This is designed originally to extract numeric values from laboratory test results, for example;
        145.2 mEq/L -> 145
    This returns a series of float values.
    """
    num_regex = r"^([+-]?\d*\.?\d+(?:[eE][-+]?\d+)?)"
    num_col = col.str.extract(num_regex, expand=False)
    num_col = pd.to_numeric(col, errors="coerce")
    return num_col


def _extract_numeric_from_text(col: pd.Series) -> pd.Series:
    """Extract numeric values from text (e.g., '145.2 mEq/L' → 145.2)"""
    num_regex = r"^([+-]?\d*\.?\d+(?:[eE][-+]?\d+)?)"
    num_col = col.str.extract(num_regex, expand=False)
    num_col = pd.to_numeric(num_col, errors="coerce")
    return num_col


def _extract_lab_values(df: pd.DataFrame, keywords: list[str], units: list[str]) -> pd.DataFrame:
    """
    Extracts lab values from simulation result table using keywords and units.

    Args:
        df (pd.DataFrame): Input table with 'text' and 'result' columns.
        keywords (list[str]): Substrings to match lab test names (case-insensitive AND).
        units (list[str]): Valid units (e.g., 'mmol/L') matched case-insensitively at the end of result.

    Returns:
        pd.DataFrame: Filtered lab values with ['simulation_number', 'timestamp', 'numeric'].
    """
    # Filter by text (all keywords must be present)
    kw_mask = df["text"].str.contains(keywords[0], case=False, na=False)
    for kw in keywords[1:]:
        kw_mask &= df["text"].str.contains(kw, case=False, na=False)
    df = df[kw_mask]

    # Filter by result unit (case-insensitive)
    unit_mask = df["result"].str.lower().str.strip().str.endswith(
        tuple(u.lower() for u in units)
    )
    df = df[unit_mask]

    # Extract numeric values
    df_labs = df.loc[:, ["simulation_number", "timestamp", "result"]].copy()
    df_labs["numeric"] = _extract_numeric_from_text(df_labs["result"])
    df_labs = df_labs[df_labs["numeric"].notna()]
    return df_labs[["simulation_number", "timestamp", "numeric"]]



def _render_timeline_html(df: pd.DataFrame):
    """Renders a simulated timeline as HTML from the DataFrame."""
    df["time_str"] = df["timestamp"].dt.strftime(config.PY_DATETIME_FORMAT)

    # Initialize html
    tl_content = ""
    df_without_dmg = df.loc[df["type"] != 0]

    for time_str, time_df in df_without_dmg.groupby("time_str"):
        # Record type grouping within the same time
        for record_type, type_df in time_df.groupby("type"):
            color = RECORD_TYPE_COLORS.get(record_type, "#ffffff")
            icon = RECORD_TYPE_ICONS.get(record_type, "")
            title = RECORD_TYPE_LABELS.get(record_type, "")
            descr = ""
            # Specific record processing based on type
            # Admission
            if record_type == 1:
                # Nothing is included in the lines for admission
                descr = "Admitted"
            # Discharge
            elif record_type == 2:
                # NOTE: There should be only one row
                for _, row in type_df.iterrows():
                    dsc_result_code = row["result"].strip()
                    dsc_result = DISCHARGE_RESULT_DICT.get(
                        dsc_result_code, "(not found)"
                    )
                    descr += dsc_result + "<br>"
            # Diagnosis
            elif record_type == 3:
                for _, row in type_df.iterrows():
                    dx_name = row["text"].strip()
                    descr += dx_name + "<br>"
            # Medication order
            elif record_type in [4, 5]:
                for _, row in type_df.iterrows():
                    drug_name = row["text"].strip()
                    descr += drug_name + "<br>"
            # Lab test
            elif record_type == 6:
                for _, row in type_df.iterrows():
                    lab_name = row["text"].strip()
                    lab_result = row["result"].replace("no_unit", "").strip()
                    descr += f"{lab_name}: {lab_result}<br>"
            # EOT
            else:
                descr = "End of follow-up"

            # Remove the final <br> if lines is not empty
            if descr:
                descr = descr.rstrip("<br>")

            # Time block HTML generation
            time_html = TL_TEMPLATE.format(
                color=color, icon=icon, time=time_str, title=title, descr=descr
            )
            tl_content += time_html

    tl_complete_html = f"<ul>{tl_content}</ul>"

    # Return the generated HTML marked as safe
    return mark_safe(tl_complete_html)


def _render_all_graphs(df: pd.DataFrame):
    """Computes data for chart rendering."""
    # Prepare variables
    n_sim = df["simulation_number"].nunique()
    df_without_dmg = df.loc[df["type"] != 0]
    data = {
        "discharge": {
            "values": {
                "all": [],
                "death": [],
            },
            "labels": [],
        },
        "broad_antibiotics": {
            "values": {
                "all": [],
            },
            "labels": [],
        },
        "serum_sodium": {
            "values": {
                "high": [],
                "median": [],
                "low": [],
            },
            "labels": [],
        },
        "serum_potassium": {
            "values": {
                "high": [],
                "median": [],
                "low": [],
            },
            "labels": [],
        },
    }

    # Cumulative events
    df_without_dmg["date"] = df_without_dmg["timestamp"].dt.floor("D")
    unique_dates = df_without_dmg["date"].sort_values(ascending=True).unique()
    for date in unique_dates:
        date_str = date.strftime("%b %-d")
        cum_date_df = df_without_dmg.loc[df_without_dmg["date"] <= date]
        date_df = df_without_dmg.loc[df_without_dmg["date"] == date]

        # Discharges
        dsc_data = data["discharge"]
        dsc_df = cum_date_df.loc[cum_date_df["code"] == "[DSC]"]
        n_total_discharges = dsc_df["simulation_number"].nunique()
        n_expired = dsc_df.loc[
            dsc_df["result"] == "[DSC_EXP]", "simulation_number"
        ].nunique()
        all_dsc_rate = round((n_total_discharges / n_sim) * 100, 1)
        exp_dsc_rate = round((n_expired / n_sim) * 100, 1)
        dsc_data["values"]["all"].append(all_dsc_rate)
        dsc_data["values"]["death"].append(exp_dsc_rate)
        dsc_data["labels"].append(date_str)
        

        # Antibiotics
        abx_data = data["broad_antibiotics"]
        broad_abx_mask = pd.Series(False, index=cum_date_df.index)
        for c in BROAD_ABX:
            pattern = rf"\b{re.escape(c)}\b"
            broad_abx_mask |= cum_date_df["text"].str.contains(pattern, case=False, na=False, regex=True)
        broad_abx_mask &= cum_date_df["type"].isin([4, 5])
        abx_df = cum_date_df.loc[broad_abx_mask]
        n_broad_abx = abx_df["simulation_number"].nunique()
        broad_abx_rate = round((n_broad_abx / n_sim) * 100, 1)
        abx_data["values"]["all"].append(broad_abx_rate)
        abx_data["labels"].append(date_str)


        # Events by date
        # Sodium
        sodium_data = data["serum_sodium"]
        sodium_keywords = LAB_CODES["serum_sodium"]["keywords"]
        sodium_units = LAB_CODES["serum_sodium"]["units"]
        sodium_df = _extract_lab_values(date_df, keywords=sodium_keywords, units=sodium_units)
        if sodium_df.size:
            min_sodium_vals = (
                sodium_df.groupby("simulation_number")["numeric"].min().values
            )
            max_sodium_vals = (
                sodium_df.groupby("simulation_number")["numeric"].max().values
            )
            mean_sodium_vals = (
                sodium_df.groupby("simulation_number")["numeric"].mean().values
            )
            sodium_90_pctl = np.percentile(max_sodium_vals, 90)
            sodium_med = np.median(mean_sodium_vals)
            sodium_10_pctl = np.percentile(min_sodium_vals, 10)
            sodium_data["values"]["high"].append(round(sodium_90_pctl, 1))
            sodium_data["values"]["median"].append(round(sodium_med, 1))
            sodium_data["values"]["low"].append(round(sodium_10_pctl, 1))
            sodium_data["labels"].append(date_str)

        # Potassium
        potassium_data = data["serum_potassium"]
        potassium_keywords = LAB_CODES["serum_potassium"]["keywords"]
        potassium_units = LAB_CODES["serum_potassium"]["units"]
        potassium_df = _extract_lab_values(date_df, keywords=potassium_keywords, units=potassium_units)
        if potassium_df.size:
            min_potassium_vals = (
                potassium_df.groupby("simulation_number")["numeric"].min().values
            )
            max_potassium_vals = (
                potassium_df.groupby("simulation_number")["numeric"].max().values
            )
            mean_potassium_vals = (
                potassium_df.groupby("simulation_number")["numeric"].mean().values
            )
            potassium_90_pctl = np.percentile(max_potassium_vals, 90)
            potassium_med = np.median(mean_potassium_vals)
            potassium_10_pctl = np.percentile(min_potassium_vals, 10)
            potassium_data["values"]["high"].append(round(potassium_90_pctl, 1))
            potassium_data["values"]["median"].append(round(potassium_med, 1))
            potassium_data["values"]["low"].append(round(potassium_10_pctl, 1))
            potassium_data["labels"].append(date_str)

    return data


# endregion

# ==============
# Views
# ==============
# region Simulation Utils


@login_required
@csrf_protect
def simulation_page_view(request: HttpRequest):
    """Renders page for simulations."""
    if request.method == "GET":
        sim_request_form = SimulationRequestForm(user=request.user)
        sim_browse_form = SimulationBrowseForm()
        return render(
            request,
            "simulator/simulator_main.html",
            {"sim_request_form": sim_request_form,
             "sim_browse_form":sim_browse_form},
        )
    
@login_required
@csrf_protect
def browse_simulation(request: HttpRequest):
    """AJAX endpoint to browse simulation by request ID and simulation number."""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed."}, status=405)
    

    form = SimulationBrowseForm(request.POST)
    if form.is_valid():
        try:
            request_id = int(form.cleaned_data["request_id"])
            sim_no = form.cleaned_data["simulation_number"]
            sim_req = get_object_or_404(SimulationRequest, request_id=int(request_id))
            field_names = SimulationResult.get_column_names()
            records = SimulationResult.objects.filter(
                request=sim_req,
                simulation_number=sim_no,
            ).values(*field_names)
            df = pd.DataFrame.from_records(records
            
        )
            timeline_html = _render_timeline_html(df)
            return JsonResponse({"timeline_html": timeline_html}, status=200)

        except Exception as e:
            return JsonResponse(
                {"error": f"Simulation rendering failed: {str(e)}"}, status=500
            )
        
    else:
        return JsonResponse(
                {"error": f"Simulation rendering failed", "form_erros":form.errors}, status=500,
            )


@login_required
@csrf_protect
def submit_simulation_request(request: HttpRequest):
    """Submits simulation API request.
    To retrieve results, you need to poll.
    """
    if request.method == "POST":
        form = SimulationRequestForm(request.POST, user=request.user)
        if form.is_valid():
            # Get form inputs
            patient = form.cleaned_data["patient"]
            patient_id = patient.patient_id
            n_iter = form.cleaned_data["n_iter"]
            time_horizon = form.cleaned_data["time_horizon"]
            horizon_start = form.cleaned_data["horizon_start"]
            # Set payload
            payload = {
                "data": {
                    "patient_id": patient_id,
                    "n_iter": n_iter,
                    "time_horizon": time_horizon,
                    "sim_start": datetime.strftime(horizon_start, "%Y/%m/%d %H:%M"),
                }
            }
            # Post
            try:
                # Send POST request
                response = requests.post(
                    config.SIM_REQUEST_URL, json=payload, timeout=600
                )
                result_json = response.json()
                # Successful submission (status 200)
                if response.status_code == 200:
                    # Save the simulation request details in the database first
                    simulation_request_obj = SimulationRequest(
                        simulation_id=result_json["simulation_id"],
                        patient_id=patient_id,
                        user=request.user,
                        time_horizon=time_horizon,
                        horizon_start=horizon_start,
                        n_iter=n_iter,
                    )
                    simulation_request_obj.save()
                    # Add data needed for fetching results
                    # NOTE: You can only access request_id after .save(), since it is auto-generated.
                    result_json["patient_id"] = patient_id
                    result_json["request_id"] = simulation_request_obj.request_id
                    # Return response
                    return JsonResponse(result_json, status=200)
                else:
                    # Handle error from Flask API
                    logger.error(f"API request error: {response.text}")
                    return JsonResponse(
                        {
                            "status": "request error",
                            "messages": [response.text],
                            "errors": result_json.get("errors", []),
                        },
                        status=response.status_code,
                    )

            except requests.exceptions.RequestException as e:
                # Handle request exceptions
                logger.error(f"Unexpected request error: {str(e)}")
                return JsonResponse(
                    {"status": "request error", "messages": [str(e)], "errors": []},
                    status=500,
                )
        # Invalid form
        else:
            # Handle request exceptions
            return JsonResponse(
                {
                    "status": "request error",
                    "messages": ["Form error"],
                    "form_errors": {
                        field: list(errors) for field, errors in form.errors.items()
                    },
                },
                status=400,
            )


@login_required
@csrf_protect
def retrieve_simulation_results(request: HttpRequest):
    """Fetches simulation API request.
    Args:
        request (HttpRequest): HTTP request.
    """
    # Poll
    post_data = request.POST
    simulation_id = post_data.get("simulation_id")
    request_id = post_data.get("request_id")
    patient_id = post_data.get("patient_id")

    response = requests.get(
        config.SIM_POLL_URL.replace("<simulation_id>", simulation_id), timeout=60
    )

    try:
        # No.1 Simulation completed
        if response.status_code == 200:
            # Get date of birth
            dob = get_object_or_404(Patients, patient_id=patient_id).date_of_birth
            dob = pd.to_datetime(dob)

            # Create a clean dataframe from response
            result_json = response.json()
            df = pd.DataFrame(result_json)
            df["type"] = df["type"].astype(int)
            df["request_id"] = int(request_id)
            df["simulation_number"], _ = pd.factorize(df[config.COL_PID])
            df["age"] = pd.to_timedelta(df["age"], unit="ms", errors="coerce")
            df["timestamp"] = df["age"] + dob
            field_names = SimulationResult.get_column_names()
            df = df[field_names]
            
            # Save the DataFrame to the database
            engine = create_engine(config.PG_ENGINE_PARAM)
            df.to_sql(
                "simulation_results",
                con=engine,
                schema="public",
                if_exists="append",
                index=False,
            )
            

            # Render html
            # Select one simulation
            selected_sim_no = int(df["simulation_number"].median()) # Select one with the median length
            max_sim_no = int(df["simulation_number"].max())
            sampled_df = df.loc[df["simulation_number"] == selected_sim_no, :]
            timeline_html = _render_timeline_html(sampled_df)
            # Prepare data for graph rendering (use all simulations)
            graph_data = _render_all_graphs(df)
            return JsonResponse(
                {   
                    "timeline_html": timeline_html,
                    "selected_sim_no": selected_sim_no,
                    "max_sim_no": max_sim_no,
                    "graph_data": graph_data,
                },
                status=200,
            )

        # No.2 Pending/Empty/Invalid request
        elif response.status_code in [202, 204, 400]:
            return JsonResponse(
                response.json(),  # with `status`,`progress`,`errors`, etc
                status=response.status_code,
            )

        # No.3 All other unexpected status
        else:
            # Handle error from Flask API
            logger.error(f"API error: {response.text}")
            return JsonResponse(
                {"status": "error", "messages": [], "errors": [response.text]},
                status=response.status_code,
            )

    # Internal errors
    except Exception as e:
        # Handle error from Flask API
        print(response)
        logger.exception(f"Internal API error: {str(e)}")
        return JsonResponse(
            {"status": "error", "messages": [], "errors": [str(e)]},
            status=500,
        )


# endregion
