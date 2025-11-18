IF OBJECT_ID('dbo.ICUStays_Stage', 'U') IS NOT NULL
    DROP TABLE dbo.ICUStays_Stage;

CREATE TABLE dbo.ICUStays_Stage (
    row_id VARCHAR(20),
    subject_id VARCHAR(50),
    hadm_id VARCHAR(50),
    icustay_id VARCHAR(50),
    db_source VARCHAR(50),
    first_care_unit VARCHAR(50),
    last_care_unit VARCHAR(50),
    first_ward_id VARCHAR(50),
    last_ward_id VARCHAR(50),
    in_time_raw VARCHAR(50),
    out_time_raw VARCHAR(50),
    los VARCHAR(50)
);

BULK INSERT dbo.ICUStays_Stage
FROM '/var/opt/SQL_Server_Docker/mimic/ICUSTAYS/ICUSTAYS_sorted.csv'
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
        TRY_CONVERT(INT, TRY_CONVERT(NUMERIC(18, 0), NULLIF(icustay_id, ''))) AS icu_id,
        TRY_CONVERT(INT, TRY_CONVERT(NUMERIC(18, 0), NULLIF(subject_id, ''))) AS patient_id,
        TRY_CONVERT(INT, TRY_CONVERT(NUMERIC(18, 0), NULLIF(hadm_id, ''))) AS admission_id,
        TRY_CONVERT(DATETIME2(0), NULLIF(in_time_raw, '')) AS in_time,
        TRY_CONVERT(DATETIME2(0), NULLIF(out_time_raw, '')) AS out_time,
        NULLIF(LTRIM(RTRIM(first_care_unit)), '') AS first_care_unit,
        NULLIF(LTRIM(RTRIM(last_care_unit)), '') AS last_care_unit,
        TRY_CONVERT(INT, TRY_CONVERT(NUMERIC(18, 0), NULLIF(first_ward_id, ''))) AS first_ward_id,
        TRY_CONVERT(INT, TRY_CONVERT(NUMERIC(18, 0), NULLIF(last_ward_id, ''))) AS last_ward_id
    FROM dbo.ICUStays_Stage
)

INSERT INTO ICU_Stays (
    icu_id,
    patient_id,
    admission_id,
    in_time,
    out_time,
    first_care_unit,
    last_care_unit,
    first_ward_id,
    last_ward_id
)
SELECT
    c.icu_id,
    c.patient_id,
    c.admission_id,
    c.in_time,
    CASE WHEN c.out_time IS NOT NULL AND c.in_time IS NOT NULL AND c.out_time < c.in_time THEN NULL ELSE c.out_time END,
    c.first_care_unit,
    c.last_care_unit,
    c.first_ward_id,
    c.last_ward_id
FROM Converted AS c
WHERE c.icu_id IS NOT NULL
  AND c.patient_id IS NOT NULL
  AND c.admission_id IS NOT NULL
  AND c.in_time IS NOT NULL
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
        FROM ICU_Stays AS existing
        WHERE existing.icu_id = c.icu_id
    );

DROP TABLE dbo.ICUStays_Stage;
