"""Creates empty tables for demo."""

import os
import glob
from datetime import datetime
from urllib.parse import quote_plus
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm
import psycopg
from psycopg import ServerCursor
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from tqdm import tqdm


# region: const
# Formats
DATETIME_FORMAT = "%Y/%m/%d %H:%M"

# Postgres table names.
TB_PATIENTS = "patients"
TB_ADMISSIONS = "admissions"
TB_DISCHARGES = "discharges"
TB_DIAGNOSES = "diagnoses"
TB_PRESC_ORD = "prescription_orders"
TB_INJEC_ORD = "injection_orders"
TB_LAB_RES = "laboratory_results"
TB_DX_CODES = "diagnosis_codes"
TB_MED_CODES = "medication_codes"
TB_LAB_CODES = "lab_test_codes"
ALL_TB = [
    TB_PATIENTS,
    TB_ADMISSIONS,
    TB_DISCHARGES,
    TB_DIAGNOSES,
    TB_PRESC_ORD,
    TB_INJEC_ORD,
    TB_LAB_RES,
]

# Source table name patterns
SRC_PATIENT_TABLE = "patients.csv"  # <- single file (Other tables can be chunked.)
SRC_OUTPATIENT_VISIT_TABLE_PATTERN = "outpatient_visits*.csv"
SRC_ADMISSION_TABLE_PATTERN = "admission_records*.csv"
SRC_DISCHARGE_TABLE_PATTERN = "discharge_records*.csv"
SRC_DIAGNOSIS_TABLE_PATTERN = "diagnosis_records*.csv"
SRC_PRESCRIPTION_ORDER_TABLE_PATTERN = "prescription_order_records*.csv"
SRC_INJECTION_ORDER_TABLE_PATTERN = "injection_order_records*.csv"
SRC_LAB_RESULT_TABLE_PATTERN = "laboratory_test_results*.csv"

# Processed table name patterns (intermediate tables are serialized.)
VISITING_DATE_TABLE = "visiting_dates.pkl"
DEMOGRAPHIC_TABLE_PATTERN = "demographics_*.pkl"
OUTPATIENT_VISIT_TABLE_PATTERN = "outpatient_visits_*.pkl"
ADMISSION_TABLE_PATTERN = "admission_records_*.pkl"
DISCHARGE_TABLE_PATTERN = "discharge_records_*.pkl"
DIAGNOSIS_TABLE_PATTERN = "diagnosis_records_*.pkl"
PRESCRIPTION_ORDER_TABLE_PATTERN = "prescription_order_records_*.pkl"
INJECTION_ORDER_TABLE_PATTERN = "injection_order_records_*.pkl"
LAB_RESULT_TABLE_PATTERN = "laboratory_test_results_*.pkl"
LABELLED_FILE_PATTERN = "labelled_*.pkl"
EVAL_TABLE_FILE_PATTERN = "evaluation_table_*.pkl"

# Timeline file patterns
TRAJECTORY_BUNDLE_FILE_PATTERN = "timeline_bundle_*.pkl"
TRAJECTORY_STATS_PATTERN = "timeline_stats_*.json"
TRAJECTORY_METADATA = "timeline_metadata.pkl"

# Other directories
DIR_CHECKPOINTS = "checkpoints"
DIR_TENSORBOARD_LOGS = "tensorboard_logs"
DIR_TENSORBOARD_ACTIVE = "tensorboard_active"
DIR_CATALOGS = "catalogs"
DIR_LAB_STATS = "laboratory_stats"
DIR_SNAPSHOTS = "snapshots"
DIR_BLUEPRINT = "watcher_blueprint"
DIR_TRAJECTORY_BUNDLES = "timeline_bundles"

# Other paths, file names.
DX_CODE_TO_NAME = "dx_codes.csv"
MED_CODE_TO_NAME = "med_codes.csv"
LAB_CODE_TO_NAME = "lab_codes.csv"
TOTAL_PATIENT_ID_LIST = "total_patient_id_list.json"
INCLUDED_PATIENT_ID_LIST = "included_patient_id_list.json"
LAB_NUM_STATS_PATTERN = "numeric_stats_*.csv"
LAB_NONNUM_STATS_PATTERN = "nonnumeric_stats_*.csv"
LAB_PERCENTILES_PATTERN = "percentiles_*.csv"
MODEL_STATE = "model_state.pt"
TRAINING_STATE = "training_state.pt"
TRAINING_REPORT = "training_report.json"
MAIN_TRAINING_REPORT = "main_training_report.json"
CATALOG_FILE = "watcher_catalog.csv"
CATALOG_INFO_FILE = "catalog_info.json"

# Common names
TRAIN = "train"
VAL = "validation"
TEST = "test"
DX_CODE = "diagnosis_code"
MED_CODE = "medication_code"
LAB_CODE = "lab_test_code"
DMG = "demographics"
OPV = "outpatient_visits"
ADM = "admissions"
DSC = "discharges"
DX = "diagnosis"
PSC_O = "prescription_orders"
INJ_O = "injection_orders"
LAB_R = "lab_test_results"
EOT = "end_of_timeline"
PROV_SUFFIX = "(prov.)"


# Common column names
COL_ITEM_CODE = "item_code"
COL_ITEM_NAME = "item_name"
COL_RECORD_ID = "unique_record_id"
COL_PID = "patient_id"
COL_DOB = "date_of_birth"
COL_SEX = "sex"
COL_FIRST_VISIT_DATE = "first_visit_date"
COL_LAST_VISIT_DATE = "last_visit_date"
COL_DEPT = "department"
COL_TOKEN = "token"
COL_ORIGINAL_VALUE = "original_value"  # For code mapping.
COL_TOKENIZED_VALUE = "tokenized_value"
COL_TIMESTAMP = "timestamp"  # For timestamp col in cleaned table
COL_TIME_AVAILABLE = "time_available"
COL_TIMEDELTA = "timedelta"  # For timedelta col in processed table
COL_YEARS = "years"
COL_MONTHS = "months"
COL_DAYS = "days"
COL_HOURS = "hours"
COL_MINUTES = "minutes"
COL_NUMERIC = "numeric"
COL_NONNUMERIC = "nonnumeric"
COL_ORIGINAL_NUMERIC = "original_numeric"
COL_ORIGINAL_NONNUMERIC = "original_nonnumeric"
COL_TYPE = "type"  # For columns to identify record type.
COL_PRIORITY = "priority"
COL_TASK_NO = "task_number"
COL_ITEM_NO = "item_number"
COL_PROVISIONAL_FLAG = "provisional"
COL_TRAIN_PERIOD = "train_period"
COL_TEST_PERIOD = "test_period"
COL_UPDATE_PERIOD = "update_period"
COL_ROW_NO = "row_number"
COL_LABEL = "label"
COL_ADM = "admitted"
COL_INCLUDED = "included"
COL_TEXT = "text"
COL_AGE = "age"
COL_CODE = "code"
COL_RESULT = "result"

# Table names.
TB_PATIENTS = "patients"
TB_ADMISSIONS = "admissions"
TB_DISCHARGES = "discharges"
TB_DIAGNOSES = "diagnoses"
TB_PRESC_ORD = "prescription_orders"
TB_INJEC_ORD = "injection_orders"
TB_LAB_RES = "laboratory_results"
TB_DX_CODES = "diagnosis_codes"
TB_MED_CODES = "medication_codes"
TB_LAB_CODES = "lab_test_codes"

# Table definitions for code maps
MAP_PARAMS = {
    TB_DX_CODES: {
        "source_csv": DX_CODE_TO_NAME,
        "columns": {
            COL_ITEM_CODE: {
                "pandas_dtype": str,
                "sql_ops": "VARCHAR(200) UNIQUE NOT NULL",
            },
            COL_ITEM_NAME: {
                "pandas_dtype": str,
                "sql_ops": "VARCHAR(200) NOT NULL",
            },
        },
        "primary_key": COL_ITEM_CODE,
        "foreign_key": None,
    },
    TB_MED_CODES: {
        "source_csv": MED_CODE_TO_NAME,
        "columns": {
            COL_ITEM_CODE: {
                "pandas_dtype": str,
                "sql_ops": "VARCHAR(200) UNIQUE NOT NULL",
            },
            COL_ITEM_NAME: {
                "pandas_dtype": str,
                "sql_ops": "VARCHAR(200) NOT NULL",
            },
        },
        "primary_key": COL_ITEM_CODE,
        "foreign_key": None,
    },
    TB_LAB_CODES: {
        "source_csv": LAB_CODE_TO_NAME,
        "columns": {
            COL_ITEM_CODE: {
                "pandas_dtype": str,
                "sql_ops": "VARCHAR(200) UNIQUE NOT NULL",
            },
            COL_ITEM_NAME: {
                "pandas_dtype": str,
                "sql_ops": "VARCHAR(200) NOT NULL",
            },
        },
        "primary_key": COL_ITEM_CODE,
        "foreign_key": None,
    },
}

# Table definitions for clinical records
RECORD_PARAMS = {
    TB_PATIENTS: {
        "source_csv": SRC_PATIENT_TABLE,
        "id_prefix": "PT",
        "columns": {
            # Others
            COL_PID: {
                "pandas_dtype": str,
                "sql_ops": "VARCHAR(200) UNIQUE NOT NULL",
            },
            COL_SEX: {
                "pandas_dtype": str,
                "sql_ops": f"CHAR(1) NOT NULL CHECK ({COL_SEX} IN ('M', 'F', 'O', 'U', 'A', 'N'))",
            },
            "first_name": {"pandas_dtype": str, "sql_ops": "VARCHAR(50) NOT NULL"},
            "last_name": {"pandas_dtype": str, "sql_ops": "VARCHAR(50) NOT NULL"},
            COL_DOB: {"pandas_dtype": datetime, "sql_ops": "DATE NOT NULL"},
        },
        # TODO: make 'COL_PID' primary key.
        "primary_key": COL_RECORD_ID,
        "foreign_key": None,
    },
    TB_ADMISSIONS: {
        "source_csv": SRC_ADMISSION_TABLE_PATTERN,
        "id_prefix": "ADM",
        "columns": {
            COL_PID: {"pandas_dtype": str, "sql_ops": "VARCHAR(200) NOT NULL"},
            COL_TIMESTAMP: {
                "pandas_dtype": datetime,
                "sql_ops": "TIMESTAMP",
            },
            COL_DEPT: {"pandas_dtype": str, "sql_ops": "VARCHAR(200)"},
        },
        "primary_key": COL_RECORD_ID,
        "foreign_key": (COL_PID, TB_PATIENTS),
    },
    TB_DISCHARGES: {
        "source_csv": SRC_DISCHARGE_TABLE_PATTERN,
        "id_prefix": "DSC",
        "columns": {
            # Others
            COL_PID: {"pandas_dtype": str, "sql_ops": "VARCHAR(200) NOT NULL"},
            COL_TIMESTAMP: {
                "pandas_dtype": datetime,
                "sql_ops": "TIMESTAMP",
            },
            "disposition": {
                "pandas_dtype": int,
                "sql_ops": "INTEGER CHECK (disposition IN (0, 1))",
            },
        },
        "primary_key": COL_RECORD_ID,
        "foreign_key": (COL_PID, TB_PATIENTS),
    },
    TB_DIAGNOSES: {
        "source_csv": SRC_DIAGNOSIS_TABLE_PATTERN,
        "id_prefix": "DX",
        "columns": {
            COL_PID: {"pandas_dtype": str, "sql_ops": "VARCHAR(200) NOT NULL"},
            COL_TIMESTAMP: {
                "pandas_dtype": datetime,
                "sql_ops": "TIMESTAMP",
            },
            COL_ITEM_CODE: {
                "pandas_dtype": str,
                "sql_ops": "VARCHAR(200)",
            },
            COL_PROVISIONAL_FLAG: {
                "pandas_dtype": int,
                "sql_ops": f"INTEGER CHECK ({COL_PROVISIONAL_FLAG} IN (0, 1))",
            },
        },
        "primary_key": COL_RECORD_ID,
        "foreign_key": (COL_PID, TB_PATIENTS),
    },
    TB_PRESC_ORD: {
        "source_csv": SRC_PRESCRIPTION_ORDER_TABLE_PATTERN,
        "id_prefix": "PRSCORD",
        "columns": {
            COL_PID: {"pandas_dtype": str, "sql_ops": "VARCHAR(200) NOT NULL"},
            COL_TIMESTAMP: {
                "pandas_dtype": datetime,
                "sql_ops": "TIMESTAMP",
            },
            COL_ITEM_CODE: {
                "pandas_dtype": str,
                "sql_ops": "VARCHAR(200)",
            },
        },
        "primary_key": COL_RECORD_ID,
        "foreign_key": (COL_PID, TB_PATIENTS),
    },
    TB_INJEC_ORD: {
        "source_csv": SRC_INJECTION_ORDER_TABLE_PATTERN,
        "id_prefix": "INJCORD",
        "columns": {
            COL_PID: {"pandas_dtype": str, "sql_ops": "VARCHAR(200) NOT NULL"},
            COL_TIMESTAMP: {
                "pandas_dtype": datetime,
                "sql_ops": "TIMESTAMP",
            },
            COL_ITEM_CODE: {
                "pandas_dtype": str,
                "sql_ops": "VARCHAR(200)",
            },
        },
        "primary_key": COL_RECORD_ID,
        "foreign_key": (COL_PID, TB_PATIENTS),
    },
    TB_LAB_RES: {
        "source_csv": SRC_LAB_RESULT_TABLE_PATTERN,
        "id_prefix": "LABRSLT",
        "columns": {
            COL_PID: {"pandas_dtype": str, "sql_ops": "VARCHAR(200) NOT NULL"},
            COL_TIMESTAMP: {
                "pandas_dtype": datetime,
                "sql_ops": "TIMESTAMP",
            },
            COL_TIME_AVAILABLE: {
                "pandas_dtype": datetime,
                "sql_ops": "TIMESTAMP",
            },
            COL_ITEM_CODE: {
                "pandas_dtype": str,
                "sql_ops": "VARCHAR(200)",
            },
            COL_NUMERIC: {"pandas_dtype": float, "sql_ops": "numeric"},
            "unit": {"pandas_dtype": str, "sql_ops": "varchar(20)"},
            COL_NONNUMERIC: {"pandas_dtype": str, "sql_ops": "VARCHAR(200)"},
        },
        "primary_key": COL_RECORD_ID,
        "foreign_key": (COL_PID, TB_PATIENTS),
    },
}

# endregion


# region: utils
def load_db_params() -> dict:
    """Gets Postgres parameters from the environment."""
    db_params = {
        "db_user": os.environ.get("CR_USER"),
        "db_password": os.environ.get("CR_PASSWORD"),
        "db_name": os.environ.get("CR_DB"),
        "db_host": os.environ.get("CR_HOST"),
        "db_port": os.environ.get("CR_PORT"),
    }
    return db_params


def load_psycopg_params():
    """Creates params for psycopg database connection"""
    db_params = load_db_params()
    # DO NOT use quote_plus for psycopg — it's for URL strings, not plain text
    psycopg_param = (
        f"dbname={db_params['db_name']} "
        f"user={db_params['db_user']} "
        f"password={db_params['db_password']} "
        f"host={db_params['db_host']} "
        f"port={db_params['db_port']}"
    )
    return psycopg_param


def load_db_engine() -> Engine:
    """Creates an engine for sqlalchemy"""
    db_params = load_db_params()
    engine_params = "postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}".format(
        db_user=db_params["db_user"],
        db_password=quote_plus(db_params["db_password"]),
        db_host=db_params["db_host"],
        db_port=db_params["db_port"],
        db_name=db_params["db_name"],
    )
    engine = create_engine(engine_params)
    return engine


def _generate_create_table_query(
    table_name: str, table_params: dict, schema: str = "public"
) -> str:
    """
    Generate a CREATE TABLE SQL query from a dictionary definition.
    """
    columns_definitions = []

    # Generate IDs
    if table_params.get("id_prefix"):
        id_prefix = table_params["id_prefix"]
        columns_definitions.append("dummy_id SERIAL NOT NULL")
        columns_definitions.append(
            f"{COL_RECORD_ID} TEXT GENERATED ALWAYS AS ('{id_prefix}' || dummy_id) STORED UNIQUE"
        )

    # Generate column definitions
    for col_name, col_props in table_params["columns"].items():
        col_definition = f"{col_name} {col_props['sql_ops']}"
        columns_definitions.append(col_definition)

    # Add primary key constraint
    if "primary_key" in table_params and table_params["primary_key"]:
        columns_definitions.append(f"PRIMARY KEY ({table_params['primary_key']})")

    # Add foreign key constraint if exists
    if "foreign_key" in table_params and table_params["foreign_key"]:
        fk_col, fk_table = table_params["foreign_key"]  # Tuple
        fk_def = f"FOREIGN KEY ({fk_col}) REFERENCES {fk_table}({fk_col})"
        columns_definitions.append(fk_def)

    # Format the final SQL query
    joind_defs = ",\n".join(columns_definitions)
    query = f"""
    CREATE TABLE IF NOT EXISTS {schema}.{table_name} ({joind_defs});
    """

    return query.strip()


def create_schema(schema: str = "public"):
    """
    Creates the given schema if it doesn't already exist.
    """
    connection_params = load_psycopg_params()
    with psycopg.connect(connection_params) as conn:
        with conn.cursor() as cur:
            # Check if schema exists
            cur.execute(
                """
                SELECT schema_name
                FROM information_schema.schemata
                WHERE schema_name = %s;
            """,
                (schema,),
            )
            exists = cur.fetchone()
            if not exists:
                cur.execute(f"CREATE SCHEMA {schema};")
                print(f"Schema '{schema}' created.")
            else:
                print(f"Schema '{schema}' already exists.")


def table_exists(cur: ServerCursor, table: str, schema: str = "public") -> bool:
    """
    Examine if a table already exists.
    """
    query = """
        SELECT table_name from information_schema.tables
        WHERE table_name = %s AND table_schema = %s;
    """
    cur.execute(query, (table, schema))
    result = cur.fetchone()
    return bool(result)


def create_empty_tables(schema: str = None):
    """Creates empty tables to initialize the database."""
    # Set up
    connection_params = load_psycopg_params()
    if schema is None:
        schema = os.environ["CR_SCHEMA"]
    # Connect to db pylint: disable=not-context-manager
    with psycopg.connect(connection_params) as conn:
        with conn.cursor() as cur:
            for param_dict in [MAP_PARAMS, RECORD_PARAMS]:
                for table, table_params in param_dict.items():
                    table_existing = table_exists(cur, table=table, schema=schema)
                    if not table_existing:
                        # Create query
                        query = _generate_create_table_query(
                            table_name=table, table_params=table_params, schema=schema
                        )
                        cur.execute(query)
                        print(f"Table '{table}' was created.")
                    else:
                        print(f"table '{table}' already exists.")
    print("Tables created")


def delete_all_tables(schema: str = "public"):
    """Deletes all tables in the database.
    CAUTION: The deletion is permanent. DO NOT USE outside experimental settings.
    """
    connection_params = load_psycopg_params

    # Connect to db pylint: disable=not-context-manager
    with psycopg.connect(connection_params) as conn:
        with conn.cursor() as cur:
            for param_dict in [MAP_PARAMS, RECORD_PARAMS]:
                for table in param_dict:
                    table_existing = table_exists(cur, table=table, schema=schema)
                    if table_existing:
                        query = f"DROP TABLE {schema}.{table} CASCADE;"
                        cur.execute(query)
                        print(f"Table '{table}' was deleted.")

    print("Existing tables deleted.")


def _upload_single_csv(
    csv_path: str,
    table: str,
    dtype: dict,
    parse_dates: list,
    schema: str = "public",
) -> None:
    """Uploads a CSV."""
    use_cols = list(dtype.keys())
    if parse_dates:
        use_cols += parse_dates
    df = pd.read_csv(
        csv_path,
        header=0,
        dtype=dtype,
        usecols=use_cols,
        parse_dates=parse_dates,
    )
    engine = load_db_engine()
    df.to_sql(table, con=engine, schema=schema, if_exists="append", index=False)


def upload_csv(
    data_source: str,
    schema: str = "public",
    max_workers: int = 1,
):
    """Uploads records with csv files."""

    # Upload code maps
    print("Uploading code maps...")
    for table, params in MAP_PARAMS.items():
        map_path = os.path.join(data_source, params["source_csv"])
        print(f"Uploading {map_path}, ...")
        _upload_single_csv(
            csv_path=map_path,
            table=table,
            dtype={col: tp["pandas_dtype"] for col, tp in params["columns"].items()},
            parse_dates=None,
            schema=schema,
        )

    # Upload clinical records
    for table, params in RECORD_PARAMS.items():
        # Find files
        csv_path_pattern = os.path.join(data_source, params["source_csv"])
        src_files = glob.glob(csv_path_pattern)
        # Data type checks
        dtype = {}
        parse_dates = []
        for col, tp in params["columns"].items():
            if tp["pandas_dtype"] == datetime:
                parse_dates.append(col)
            else:
                dtype[col] = tp["pandas_dtype"]

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(
                    upload_csv,
                    csv_path=f,
                    table=table,
                    dtype=dtype,
                    parse_dates=parse_dates,
                    schema=schema,
                )
                for f in src_files
            ]
            for future in tqdm(
                as_completed(futures), desc=f"Uploading files to '{table}'"
            ):
                _ = future.result()


def init_db_with_csv(
    data_source: str, max_workers: int, schema="public", delete_existing=False
):
    """
    Initialize PostgreSQL database using CSV files.

    This function sets up a PostgreSQL database schema and populates it with
    tables and records from provided CSV files. It supports optional deletion
    of all existing tables before the import.

    Warnings:
        - If `delete_existing` is True, **all tables defined in the configuration will be dropped**.
          This operation is irreversible and will result in data loss.
        - Ensure that CSV files conform to the expected schema defined in `RECORD_PARAMS` and `MAP_PARAMS`.

    Note:
        - Tables will be created only if they don't already exist, unless `delete_existing` is set.
        - Column types, primary keys, and foreign keys are configured via `watcher_config`.
        - This function uses `psycopg` for schema management and `pandas.to_sql()` with SQLAlchemy for uploading data.
        - Uploading clinical record CSVs is parallelized using `ProcessPoolExecutor`.

    Args:
        data_source (str): Absolute path to the directory containing source CSV files.
        max_workers (int): Number of parallel workers for uploading clinical record files.
        schema (str, optional): Target PostgreSQL schema. Defaults to "public".
        delete_existing (bool, optional): If True, drops all existing tables in the schema before creation.


    Returns:
        None
    """

    # Delete old data
    if delete_existing:
        delete_all_tables(schema=schema)

    # Initialize tables (if not exists)
    create_schema(schema=schema)
    delete_all_tables(schema=schema)
    create_empty_tables(schema=schema)

    # Upload
    upload_csv(
        data_source=data_source,
        max_workers=max_workers,
        schema=schema,
    )


# endregion

if __name__ == "__main__":
    create_empty_tables()
