
#!/usr/bin/env python3

"""
weekly_sync.py

Weekly task synchronization job.

Flow:
    CSV
      ↓
    Validate source data
      ↓
    ClickHouse staging table
      ↓
    Validate staging data
      ↓
    Production table
      ↓
    Dashboard

Environment variables:
    SOURCE_FILE
    CH_HOST
    CH_PORT
    CH_USER
    CH_PASSWORD
    CH_DATABASE
    STAGING_TABLE
    PRODUCTION_TABLE
"""

import csv
import logging
import os
from datetime import datetime

import clickhouse_connect


# ============================================================
# Configuration
# ============================================================

SOURCE_FILE = os.getenv(
    "SOURCE_FILE",
    r"C:\Users\smanj\Downloads\SPRINGER CAPITAL\ClickHouseProblem\weekly_tasks.csv"
)

CH_HOST = os.getenv("CH_HOST", "localhost")
CH_PORT = int(os.getenv("CH_PORT", "8123"))
CH_USER = os.getenv("CH_USER", "etl")
CH_PASSWORD = os.getenv("CH_PASSWORD", "etl_password")
CH_DATABASE = os.getenv("CH_DATABASE", "default")

STAGING_TABLE = os.getenv(
    "STAGING_TABLE",
    "weekly_tasks_staging"
)

PRODUCTION_TABLE = os.getenv(
    "PRODUCTION_TABLE",
    "weekly_tasks"
)


# ============================================================
# Logging
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# ============================================================
# Required CSV columns
# ============================================================

REQUIRED_COLUMNS = [
    "task_id",
    "task_name",
    "status",
    "assigned_to",
    "due_date",
]


# ============================================================
# ClickHouse connection
# ============================================================

def get_clickhouse_client():
    logger.info(
        "Connecting to ClickHouse: %s:%s",
        CH_HOST,
        CH_PORT
    )

    client = clickhouse_connect.get_client(
        host=CH_HOST,
        port=CH_PORT,
        username=CH_USER,
        password=CH_PASSWORD,
        database=CH_DATABASE
    )

    # Test connection
    client.command("SELECT 1")

    logger.info("ClickHouse connection successful.")

    return client


# ============================================================
# CSV validation
# ============================================================

def validate_csv():
    logger.info("Checking source file: %s", SOURCE_FILE)

    if not os.path.exists(SOURCE_FILE):
        raise FileNotFoundError(
            f"Source CSV file does not exist: {SOURCE_FILE}"
        )

    if os.path.getsize(SOURCE_FILE) == 0:
        raise ValueError("Source CSV file is empty.")

    rows = []

    # utf-8-sig handles normal UTF-8 as well as Excel-generated CSVs
    with open(
        SOURCE_FILE,
        "r",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        reader = csv.DictReader(file)

        if reader.fieldnames is None:
            raise ValueError("CSV file has no header row.")

        missing_columns = [
            column
            for column in REQUIRED_COLUMNS
            if column not in reader.fieldnames
        ]

        if missing_columns:
            raise ValueError(
                f"CSV is missing required columns: {missing_columns}"
            )

        for line_number, row in enumerate(reader, start=2):

            # Check required values
            for column in REQUIRED_COLUMNS:
                value = row.get(column)

                if value is None or not value.strip():
                    raise ValueError(
                        f"Missing value for '{column}' "
                        f"at CSV line {line_number}"
                    )

            # Validate date
            try:
                row["due_date"] = datetime.strptime(
                    row["due_date"].strip(),
                    "%Y-%m-%d"
                ).date()

            except ValueError as exc:
                raise ValueError(
                    f"Invalid due_date '{row['due_date']}' "
                    f"at CSV line {line_number}. "
                    f"Expected YYYY-MM-DD."
                ) from exc

            # Clean string fields
            row["task_id"] = row["task_id"].strip()
            row["task_name"] = row["task_name"].strip()
            row["status"] = row["status"].strip()
            row["assigned_to"] = row["assigned_to"].strip()

            rows.append(row)

    if not rows:
        raise ValueError("CSV contains no data records.")

    logger.info(
        "CSV validation successful. Records found: %d",
        len(rows)
    )

    return rows


# ============================================================
# Create ClickHouse tables
# ============================================================

def create_tables(client):

    logger.info("Creating staging table if required.")

    client.command(
        f"""
        CREATE TABLE IF NOT EXISTS {STAGING_TABLE}
        (
            task_id String,
            task_name String,
            status String,
            assigned_to String,
            due_date Date
        )
        ENGINE = MergeTree
        ORDER BY task_id
        """
    )

    logger.info("Creating production table if required.")

    client.command(
        f"""
        CREATE TABLE IF NOT EXISTS {PRODUCTION_TABLE}
        (
            task_id String,
            task_name String,
            status String,
            assigned_to String,
            due_date Date
        )
        ENGINE = MergeTree
        ORDER BY task_id
        """
    )


# ============================================================
# Load staging table
# ============================================================

def load_staging(client, rows):

    logger.info("Clearing staging table.")

    client.command(
        f"TRUNCATE TABLE {STAGING_TABLE}"
    )

    logger.info(
        "Loading %d records into staging table.",
        len(rows)
    )

    data = []

    for row in rows:
        data.append(
            [
                row["task_id"],
                row["task_name"],
                row["status"],
                row["assigned_to"],
                row["due_date"],
            ]
        )

    client.insert(
        STAGING_TABLE,
        data,
        column_names=[
            "task_id",
            "task_name",
            "status",
            "assigned_to",
            "due_date",
        ]
    )

    logger.info("Staging load completed successfully.")


# ============================================================
# Validate staging table
# ============================================================

def validate_staging(client):

    logger.info("Validating staging table.")

    count = client.query(
        f"SELECT count() FROM {STAGING_TABLE}"
    ).result_rows[0][0]

    if count == 0:
        raise ValueError(
            "Staging table contains zero records."
        )

    # Check for empty task IDs
    empty_ids = client.query(
        f"""
        SELECT count()
        FROM {STAGING_TABLE}
        WHERE task_id = ''
        """
    ).result_rows[0][0]

    if empty_ids > 0:
        raise ValueError(
            f"Staging validation failed: "
            f"{empty_ids} records have empty task_id."
        )

    # Check for duplicate task IDs
    duplicate_ids = client.query(
        f"""
        SELECT count()
        FROM
        (
            SELECT task_id
            FROM {STAGING_TABLE}
            GROUP BY task_id
            HAVING count() > 1
        )
        """
    ).result_rows[0][0]

    if duplicate_ids > 0:
        raise ValueError(
            f"Staging validation failed: "
            f"{duplicate_ids} duplicate task IDs found."
        )

    logger.info(
        "Staging validation successful. Records: %d",
        count
    )


# ============================================================
# Refresh production table
# ============================================================

def refresh_production(client):

    logger.info("Refreshing production table.")

    client.command(
        f"TRUNCATE TABLE {PRODUCTION_TABLE}"
    )

    client.command(
        f"""
        INSERT INTO {PRODUCTION_TABLE}
        SELECT
            task_id,
            task_name,
            status,
            assigned_to,
            due_date
        FROM {STAGING_TABLE}
        """
    )

    logger.info(
        "Production table refreshed successfully."
    )


# ============================================================
# Verify production table
# ============================================================

def verify_production(client):

    logger.info("Verifying production table.")

    production_count = client.query(
        f"SELECT count() FROM {PRODUCTION_TABLE}"
    ).result_rows[0][0]

    if production_count == 0:
        raise ValueError(
            "Production table contains zero records."
        )

    logger.info(
        "Production validation successful. Records: %d",
        production_count
    )


# ============================================================
# Main
# ============================================================

def main():

    client = None

    logger.info("=" * 60)
    logger.info("Weekly task synchronization started.")
    logger.info("=" * 60)

    try:

        # Step 1: Validate CSV
        rows = validate_csv()

        # Step 2: Connect to ClickHouse
        client = get_clickhouse_client()

        # Step 3: Create tables
        create_tables(client)

        # Step 4: Load staging
        load_staging(client, rows)

        # Step 5: Validate staging
        validate_staging(client)

        # Step 6: Refresh production
        refresh_production(client)

        # Step 7: Verify production
        verify_production(client)

        logger.info("=" * 60)
        logger.info(
            "Weekly task synchronization completed successfully."
        )
        logger.info("=" * 60)

    except Exception as exc:

        logger.exception(
            "WEEKLY SYNC FAILED: %s",
            exc
        )

        raise

    finally:

        if client is not None:
            try:
                client.close()
                logger.info("ClickHouse connection closed.")
            except Exception:
                pass


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":
    main()