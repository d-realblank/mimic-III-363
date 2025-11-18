IF OBJECT_ID('dbo.NoteEvents_Stage', 'U') IS NOT NULL
    DROP TABLE dbo.NoteEvents_Stage;

CREATE TABLE dbo.NoteEvents_Stage (
    row_id VARCHAR(20),
    subject_id VARCHAR(50),
    hadm_id VARCHAR(50),
    chart_date_raw VARCHAR(50),
    chart_time_raw VARCHAR(50),
    store_time_raw VARCHAR(50),
    category VARCHAR(50),
    description VARCHAR(300),
    cgid VARCHAR(50),
    is_error_raw NVARCHAR(50),
    note_text NVARCHAR(MAX)
);

BULK INSERT dbo.NoteEvents_Stage
FROM '/var/opt/SQL_Server_Docker/mimic/NOTEEVENTS/NOTEEVENTS_sorted.csv'
WITH (
    DATAFILETYPE = 'char',
    FIELDTERMINATOR = ',',
    ROWTERMINATOR = '0x0d0a',
    FIRSTROW = 2,
    FIELDQUOTE = '"',
    TABLOCK
);

;WITH Converted AS (
    SELECT
        TRY_CONVERT(INT, TRY_CONVERT(NUMERIC(18, 0), NULLIF(row_id, ''))) AS note_id,
        TRY_CONVERT(INT, TRY_CONVERT(NUMERIC(18, 0), NULLIF(subject_id, ''))) AS patient_id,
        TRY_CONVERT(INT, TRY_CONVERT(NUMERIC(18, 0), NULLIF(hadm_id, ''))) AS admission_id,
        TRY_CONVERT(INT, TRY_CONVERT(NUMERIC(18, 0), NULLIF(cgid, ''))) AS caregiver_id,
        COALESCE(
            TRY_CONVERT(DATETIME2(0), NULLIF(chart_date_raw, '')),
            TRY_CONVERT(DATETIME2(0), NULLIF(store_time_raw, '')),
            TRY_CONVERT(DATETIME2(0), NULLIF(chart_time_raw, ''))
        ) AS create_date,
        COALESCE(
            TRY_CONVERT(DATETIME2(0), NULLIF(chart_time_raw, '')),
            TRY_CONVERT(DATETIME2(0), NULLIF(store_time_raw, '')),
            TRY_CONVERT(DATETIME2(0), NULLIF(chart_date_raw, ''))
        ) AS create_time,
        NULLIF(LTRIM(RTRIM(category)), '') AS category,
        NULLIF(LTRIM(RTRIM(description)), '') AS description,
        note_text,
        CASE WHEN NULLIF(LTRIM(RTRIM(is_error_raw)), '') IN ('1', 'Y', 'YES', 'ERROR', 'TRUE') THEN 'TRUE' ELSE 'FALSE' END AS is_error
    FROM dbo.NoteEvents_Stage
)

INSERT INTO Note_Events (
    note_id,
    patient_id,
    admission_id,
    caregiver_id,
    create_date,
    create_time,
    category,
    description,
    text,
    is_error
)
SELECT
    c.note_id,
    c.patient_id,
    c.admission_id,
    c.caregiver_id,
    c.create_date,
    c.create_time,
    c.category,
    c.description,
    c.note_text,
    c.is_error
FROM Converted AS c
WHERE c.note_id IS NOT NULL
  AND c.patient_id IS NOT NULL
  AND c.admission_id IS NOT NULL
  AND c.create_date IS NOT NULL
  AND EXISTS (
        SELECT 1
        FROM Patients AS p
        WHERE p.patient_id = c.patient_id
    )
  AND EXISTS (
        SELECT 1
        FROM Admissions AS a
        WHERE a.admission_id = c.admission_id
    )
  AND NOT EXISTS (
        SELECT 1
        FROM Note_Events AS existing
        WHERE existing.note_id = c.note_id
    );

DROP TABLE dbo.NoteEvents_Stage;
