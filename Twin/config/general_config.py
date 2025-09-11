"""
Twin settings
"""
import os
from django.conf import settings # Things in Django's settings.py

# ==================
# Twin Settings 
# ==================
# region Twin Settings
# Formats
PG_DATE_FORMAT = "%Y-%m-%d" # DATE
PG_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S" # TIMESTAMP
PY_DATETIME_FORMAT = "%Y/%m/%d %H:%M"

# Sqlalchemy engine template
CR_DB = settings.DATABASES["clinical_records"]
CR_ENGINE_PARAM = (
    f"postgresql+psycopg://{CR_DB['USER']}:{CR_DB['PASSWORD']}@{CR_DB['HOST']}:{CR_DB['PORT']}/{CR_DB['NAME']}"
)
PG_DB = settings.DATABASES["default"]
PG_ENGINE_PARAM = (
    f"postgresql+psycopg://{PG_DB['USER']}:{PG_DB['PASSWORD']}@{PG_DB['HOST']}:{PG_DB['PORT']}/{PG_DB['NAME']}"
)

# Simulation API settings
sim_host = os.environ.get("SIM_API_HOST")
sim_port = os.environ.get("SIM_API_PORT")

if sim_host and sim_port:
    SIM_REQUEST_URL = f"http://{sim_host}:{sim_port}/watcher_api/monte_carlo"
    SIM_POLL_URL = f"http://{sim_host}:{sim_port}/watcher_api/result/<simulation_id>"
else:
    # API integration is disabled if not configured
    SIM_REQUEST_URL = ""
    SIM_POLL_URL = ""

# Columns
COL_PID = "patient_id"
COL_ITEM_CODE = "item_code"
COL_ITEM_NAME = "item_name"

# endregion