# Weekly Task Synchronization - ClickHouse

## Acumen Strategy - Tech Operations

A safe and validated Python-based ETL process for loading weekly task exports into ClickHouse.

The original synchronization process directly loaded CSV data into the production table. The improved implementation introduces input validation, staging, data-quality checks, logging, and production verification.

---

## 1. Project Overview

The weekly synchronization job runs every Monday at 05:00.

It performs the following operations:

1. Reads the weekly CSV export.
2. Validates the source file.
3. Validates required columns.
4. Validates the input records.
5. Connects to ClickHouse.
6. Loads the data into a staging table.
7. Validates the staging data.
8. Refreshes the production table.
9. Verifies the production data.
10. Logs the complete execution.

### Data Flow

```text
Weekly CSV
    |
    v
Input Validation
    |
    v
Staging Table
    |
    v
Data Validation
    |
    v
Production Table
    |
    v
Dashboard
2. Problem in the Original Script

The original weekly_sync.py had several problems:

Hard-coded source file path
Hard-coded ClickHouse connection details
No source-file existence check
No required-column validation
No data-quality validation
No staging table
Direct production modification
Limited error handling
No clear recovery strategy
Risk of leaving production empty after a failed refresh
3. Improved Solution

The corrected implementation introduces:

Environment-based configuration
Source-file validation
Required-column validation
Empty-data validation
Date validation
Duplicate task_id detection
Staging table
Staging validation
Production verification
Logging
Repeatable execution
Safe re-run procedure
4. Project Structure
ClickHouseProblem/
│
├── weekly_sync.py
├── weekly_tasks.csv
├── Staging_Table_SQL.sql
│
├── Problem_FaultAnalysis.doc
├── Root_Cause_Explanation.doc
├── Data_Validation_Strategy.doc
├── Safe_Re-run_Strategy.doc
├── ClickHouse_Configuration.doc
├── Testing_Evidence.doc
├── Final_Recommendations.doc
│
└── README.md
5. Requirements
Software
Windows
Python 3.x
ClickHouse
Docker Desktop
Python package: clickhouse-connect
Python Package

Install the ClickHouse client with:

py -m pip install clickhouse-connect

Verify installation:

py -m pip show clickhouse-connect
6. ClickHouse Setup

The project uses ClickHouse running in Docker.

Docker Image
clickhouse/clickhouse-server:latest
Container
clickhouse
Ports
Port	Purpose
8123	HTTP interface
9000	Native ClickHouse protocol
9009	Inter-server communication

Check whether the container is running:

docker ps --filter "name=clickhouse"

Expected status:

Up

If the container is stopped:

docker start clickhouse
7. Verify ClickHouse

Check the ClickHouse version:

docker exec clickhouse clickhouse-client --user default --query "SELECT version()"

Expected result:

26.9.12.8
8. ClickHouse Tables

The project uses two tables.

Staging Table
weekly_tasks_staging

Purpose:

Receive source data
Validate data
Detect data-quality problems
Prevent invalid records from immediately reaching production
Production Table
weekly_tasks

Purpose:

Store the validated weekly task data
Provide data for the dashboard
9. Table Schema

Both tables use the following schema:

Column	Type
task_id	String
task_name	String
status	String
assigned_to	String
due_date	Date

The tables use:

ENGINE = MergeTree
ORDER BY task_id
10. Environment Configuration

The synchronization script reads its configuration from environment variables.

Set the following in PowerShell:

$env:SOURCE_FILE="C:\Users\smanj\Downloads\SPRINGER CAPITAL\ClickHouseProblem\weekly_tasks.csv"

$env:CH_HOST="localhost"
$env:CH_PORT="8123"
$env:CH_USER="etl"
$env:CH_PASSWORD="etl_password"
$env:CH_DATABASE="default"

Verify the variables if required:

$env:CH_HOST
$env:CH_PORT
$env:CH_USER
$env:CH_DATABASE
$env:SOURCE_FILE
11. Source CSV Format

The CSV must contain the following columns:

task_id
task_name
status
assigned_to
due_date

Example:

task_id,task_name,status,assigned_to,due_date
T001,Prepare report,Completed,John,2026-10-05
T002,Review dashboard,Pending,Mary,2026-10-06

The due_date format must be:

YYYY-MM-DD

Example:

2026-10-07
12. Validation Checks

Before loading data into ClickHouse, the script validates:

File validation
Source file exists
CSV can be opened
Schema validation

Required columns:

task_id
task_name
status
assigned_to
due_date
Data validation
CSV is not empty
task_id is not empty
task_id values are not duplicated
due_date contains valid dates
13. Running the Synchronization

Navigate to the project folder:

cd "C:\Users\smanj\Downloads\SPRINGER CAPITAL\ClickHouseProblem"

Run:

py weekly_sync.py
14. Expected Successful Output

A successful execution should contain messages similar to:

Weekly task synchronization started.

CSV validation successful. Records found: 10

ClickHouse connection successful.

Creating staging table if required.

Creating production table if required.

Loading 10 records into staging table.

Staging load completed successfully.

Staging validation successful. Records: 10

Production table refreshed successfully.

Production validation successful. Records: 10

Weekly task synchronization completed successfully.

ClickHouse connection closed.
15. Verify Staging Data

Check the staging record count:

docker exec clickhouse clickhouse-client --user default --query "SELECT count() FROM weekly_tasks_staging"

Expected result for the test dataset:

10

View the records:

docker exec clickhouse clickhouse-client --user default --query "SELECT * FROM weekly_tasks_staging ORDER BY task_id"
16. Verify Production Data

Check the production record count:

docker exec clickhouse clickhouse-client --user default --query "SELECT count() FROM weekly_tasks"

Expected result:

10

View production records:

docker exec clickhouse clickhouse-client --user default --query "SELECT * FROM weekly_tasks ORDER BY task_id"
17. Verify Table Structure

Run:

docker exec clickhouse clickhouse-client --user default --query "DESCRIBE TABLE weekly_tasks_staging"

Expected columns:

task_id       String
task_name     String
status        String
assigned_to   String
due_date      Date
18. Staging Validation Queries

The Staging_Table_SQL.sql file contains validation queries.

Record count
SELECT count()
FROM weekly_tasks_staging;
Empty task IDs
SELECT count()
FROM weekly_tasks_staging
WHERE task_id = '';

Expected:

0
Duplicate task IDs
SELECT
    task_id,
    count() AS duplicate_count
FROM weekly_tasks_staging
GROUP BY task_id
HAVING count() > 1;

Expected:

No rows
19. Safe Re-run Procedure

If the synchronization fails:

Read the error in the terminal/log.
Identify the failed stage.
Correct the problem.
Confirm ClickHouse is running.
Run the script again.

Example:

py weekly_sync.py

The staging table is rebuilt/refreshed with the current source dataset.

The process validates the data before production refresh.

20. Failure Scenarios
Missing CSV

If the CSV is missing, the script stops.

Expected behavior:

ERROR: Source file does not exist
Missing Required Column

If a required column is missing, the script stops rather than loading incomplete data.

Duplicate Task ID

Duplicate IDs are detected during staging validation.

The production refresh should not proceed with invalid staging data.

Invalid Date

A date that does not follow:

YYYY-MM-DD

is rejected.

ClickHouse Unavailable

If ClickHouse cannot be reached, the script reports the connection error and stops.

21. Testing Summary

The corrected implementation was successfully tested with a 10-record CSV.

Test	Result
Source file validation	PASS
CSV validation	PASS
Required column validation	PASS
ClickHouse connection	PASS
Staging table creation	PASS
Staging load	PASS
Staging validation	PASS
Production refresh	PASS
Production verification	PASS

Final test result:

PASS
22. Known Production Improvement

The current implementation refreshes production using a:

TRUNCATE + INSERT

approach.

Although the staging validation makes the workflow safer, there is still a small risk if the production table is truncated and the subsequent insert fails.

For production deployment, the recommended approach is:

CSV
 ↓
Staging
 ↓
Validation
 ↓
Temporary Production Table
 ↓
Validation
 ↓
Atomic Replacement
 ↓
Dashboard

This prevents the dashboard from being left with an empty production table after a failed refresh.

23. Production Recommendations

For production deployment, implement:

Atomic production replacement
Secure secret management
Least-privilege database permissions
Automated retry
Failure alerts
Execution monitoring
Data reconciliation
Audit logging
Backup/recovery
Job execution history
24. Scheduling

The intended schedule is:

Every Monday at 05:00

The scheduler should execute:

py weekly_sync.py

Production scheduling should also include:

Retry on failure
Timeout
Failure notification
Execution logging
25. Deliverables

The project contains the following deliverables:

weekly_sync.py
Staging_Table_SQL.sql
Problem_FaultAnalysis.doc
Root_Cause_Explanation.doc
Data_Validation_Strategy.doc
Safe_Re-run_Strategy.doc
ClickHouse_Configuration.doc
Testing_Evidence.doc
Final_Recommendations.doc
README.md
weekly_tasks.csv
26. Final Status

The weekly synchronization workflow has been successfully tested.

Test dataset:

10 records

Staging records:

10

Production records:

10

ClickHouse version:

26.9.12.8

Final status:

SUCCESS
27. Conclusion

The original unsafe direct-load process has been improved into a controlled ETL workflow.

The solution now provides:

Input validation
Schema validation
Data-quality validation
Staging isolation
ClickHouse connectivity
Dedicated ETL user
Logging
Production verification
Repeatable execution
Failure detection
Safe re-run capability

The next major production-hardening step is to implement atomic production replacement so that the live dashboard data remains protected even if the final production load fails.


