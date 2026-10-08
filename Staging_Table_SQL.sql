-- ============================================================
-- Staging_Table_SQL.sql
-- Weekly Task Synchronization Project
-- Acumen Strategy - Tech Operations
------------------------------------

-- Purpose:
-- Temporary staging area for weekly task data before
-- validation and promotion to the production table.
-- ============================================================

CREATE TABLE IF NOT EXISTS weekly_tasks_staging
(
task_id String,
task_name String,
status String,
assigned_to String,
due_date Date
)
ENGINE = MergeTree
ORDER BY task_id;

-- ============================================================
-- Validation Queries
-- ============================================================

-- Total records loaded into staging
SELECT count()
FROM weekly_tasks_staging;

-- Check for empty task IDs
SELECT count()
FROM weekly_tasks_staging
WHERE task_id = '';

-- Check for duplicate task IDs
SELECT
task_id,
count() AS duplicate_count
FROM weekly_tasks_staging
GROUP BY task_id
HAVING count() > 1;

-- Review staged records
SELECT *
FROM weekly_tasks_staging
ORDER BY task_id;

-- ============================================================
-- Clear staging table before next load
-- ============================================================

TRUNCATE TABLE weekly_tasks_staging;

-- ============================================================
-- Promote validated data to production
-- ============================================================

INSERT INTO weekly_tasks
SELECT
task_id,
task_name,
status,
assigned_to,
due_date
FROM weekly_tasks_staging;

-- ============================================================
-- Verify production load
-- ============================================================

SELECT count()
FROM weekly_tasks;
