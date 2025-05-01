import requests
import logging
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
<li style="--accent-color: {color}">
  <div class="time d-flex align-items-center gap-2">
    <i class="{icon}" style="font-size: 1.5rem;"></i>
    <span>{time}</span>
  </div>
  <div class="title">{title}</div>
  <div class="descr">{descr}</div>
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
            "J01XA",  # Glycopeptide antibiotics (including vancomycin and teicoplanin)
            "J01XX08",  # linezolid
            "J01XX09",  # daptomycin
        ]

LAB_CODES = {
    "serum_sodium": "3H0100000023---01",
    # Potassium
    "serum_potassium": "3H0150000023---01",
    # Chloride
    "serum_chloride": "3H0200000023---01",
}

# Neutropenia
# ANC = WBC * neutrophil fraction
NEUTROPENIA_SETS = {
    "wbc_code": "2A9900000019---52",  # CBC (complete blood count), , whole blood(with additive), white blood cell count
    "neutrophil_code": [
        "2A1600000019---51",  # whole blood result, unit = %
        "2A1600000034---51",  # blood smear result, unit = %. This one is less frequent.
    ],
    "wbc_unit": "×10^3/μL",
    "wbc_const": 1000,
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


def _extract_lab_values(df: pd.DataFrame, target_code: str, unit: str) -> pd.DataFrame:
    """Extract target laboratory results from a table.
    Args:
        df (pd.DataFrame): Input table.
        target_code (str): Target code.
        unit (str): Unit.
    Returns:
        df_labs (pd.DataFrame): Table with target laboratory test results only.
    """
    lab_mask = (df["code"] == target_code) & (df["result"].str.endswith(unit))
    df_labs = df.loc[lab_mask, ["simulation_number", "timestamp", "result"]].copy()
    df_labs["numeric"] = _extract_numeric_from_text(df_labs["result"])
    df_labs = df_labs.loc[df_labs["numeric"].notna()]
    df_labs = df_labs[["simulation_number", "timestamp", "numeric"]]

    return df_labs


def _compute_anc(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate absolute nutrophil counts using wbc and neutrophil fractions.
    If duplicated counts are found, lower ones are selected.
    Args:
        df (pd.DataFrame): Input table.
    Returns:
        ancs (pd.DataFrame): Output table with absolute neutrophil counts.
            This table only contains three columns: patient ID, age and anc.
            (* anc for absolute neutrophil counts.)
    """
    wbc_code = NEUTROPENIA_SETS["wbc_code"]
    wbc_unit = NEUTROPENIA_SETS["wbc_unit"]
    wbc_const = NEUTROPENIA_SETS["wbc_const"]
    neut_coudes = NEUTROPENIA_SETS["neutrophil_code"]
    # Select WBCs
    wbcs = df.loc[
        (df["code"] == wbc_code) & (df["result"].str.endswith(wbc_unit))
    ].copy()
    wbcs["numeric"] = wbcs["result"].str.extract(r"(\d+\.?\d*)", expand=True)
    wbcs["numeric"] = pd.to_numeric(wbcs["numeric"], errors="coerce")
    wbcs = wbcs.loc[~wbcs["numeric"].isna()]
    wbcs["numeric"] = wbcs["numeric"] * wbc_const
    wbcs = wbcs.rename(columns={"numeric": "wbc"})
    wbcs = wbcs[["simulation_number", "timestamp", "wbc"]]
    # Select neutrophil fractions
    neuts = df.loc[
        (df["code"].isin(neut_coudes)) & (df["result"].str.endswith("%"))
    ].copy()
    neuts["numeric"] = neuts["result"].str.extract(r"(\d+\.?\d*)", expand=True)
    neuts["numeric"] = pd.to_numeric(neuts["numeric"], errors="coerce")
    neuts = neuts.loc[~neuts["numeric"].isna()]
    neuts["numeric"] = neuts["numeric"] * 0.01  # % -> fraction
    neuts = neuts.rename(columns={"numeric": "neut"})
    neuts = neuts[["simulation_number", "timestamp", "neut"]]
    # Compute ANC
    ancs = pd.merge(wbcs, neuts, how="left", on=["simulation_number", "timestamp"])
    ancs["anc"] = ancs["wbc"] * ancs["neut"]
    ancs = ancs[["simulation_number", "timestamp", "anc"]]
    # Sort and drop duplicates (* Latest value comes first)
    ancs = ancs.sort_values(
        ["simulation_number", "timestamp", "anc"], ascending=[True, False, True]
    )
    ancs = ancs.drop_duplicates(["simulation_number", "timestamp"], keep="first")
    # Drop missing ANC (either wbc or neutrofil fraction missing)
    ancs = ancs.dropna(subset=["anc"])

    return ancs


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
        "anc": {
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
        broad_abx_mask = pd.Series(
            np.full(len(cum_date_df), False), index=cum_date_df.index
        )
        for c in BROAD_ABX:
            broad_abx_mask = broad_abx_mask | cum_date_df["code"].str.startswith(c)
        broad_abx_mask = broad_abx_mask & cum_date_df["type"].isin([4, 5])
        abx_df = cum_date_df.loc[broad_abx_mask]
        n_borad_abx = abx_df["simulation_number"].nunique()
        broad_abx_rate = round((n_borad_abx / n_sim) * 100, 1)
        abx_data["values"]["all"].append(broad_abx_rate)
        abx_data["labels"].append(date_str)

        # Events by date
        # Sodium
        sodium_data = data["serum_sodium"]
        sodium_code = LAB_CODES["serum_sodium"]
        sodium_df = _extract_lab_values(date_df, target_code=sodium_code, unit="mmol/L")
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

        # ANC
        anc_data = data["anc"]
        anc_df = _compute_anc(df=date_df)
        if anc_df.size:
            min_anc_vals = anc_df.groupby("simulation_number")["anc"].min().values
            max_anc_vals = anc_df.groupby("simulation_number")["anc"].max().values
            mean_anc_vals = anc_df.groupby("simulation_number")["anc"].mean().values
            anc_90_pctl = np.percentile(max_anc_vals, 90)
            anc_med = np.median(mean_anc_vals)
            anc_10_pctl = np.percentile(min_anc_vals, 10)
            anc_data["values"]["high"].append(int(anc_90_pctl))
            anc_data["values"]["median"].append(int(anc_med))
            anc_data["values"]["low"].append(int(anc_10_pctl))
            anc_data["labels"].append(date_str)

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
    """Renders page for simulations."""
    if request.method == "POST":
        form = SimulationBrowseForm(request.POST, user=request.user)
        


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
            df["request_id"] = request_id
            df["simulation_number"], _ = pd.factorize(df[config.COL_PID])
            df["age"] = pd.to_timedelta(df["age"], unit="ms", errors="coerce")
            df["timestamp"] = df["age"] + dob
            field_names = SimulationResult.get_column_names()
            df = df[field_names]

            # Save the DataFrame to the database
            engine = create_engine(config.CR_ENGINE_PARAM)
            df.to_sql(
                "simulation_results",
                con=engine,
                if_exists="append",
                index=False,
            )

            # Render html
            # Select one simulation
            unique_sim_no = df["simulation_number"].unique()
            max_sim_no = int(unique_sim_no.max())
            median_sim_no = int(np.median(unique_sim_no))
            sampled_df = df.loc[df["simulation_number"] == median_sim_no, :]
            timeline_html = _render_timeline_html(sampled_df)
            # Prepare data for graph rendering (use all simulations)
            graph_data = _render_all_graphs(df)

            return JsonResponse(
                {
                    "timeline_html": timeline_html,
                    "selected_sim_no": median_sim_no,
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
        logger.error(f"Internal API error: {str(e)}")
        return JsonResponse(
            {"status": "error", "messages": [], "errors": [str(e)]},
            status=500,
        )


# endregion
