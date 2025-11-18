IF OBJECT_ID('dbo.Admissions_Stage', 'U') IS NOT NULL
    DROP TABLE dbo.Admissions_Stage;

CREATE TABLE dbo.Admissions_Stage (
    row_id VARCHAR(20),
    subject_id VARCHAR(50),
    hadm_id VARCHAR(50),
    admit_time_raw VARCHAR(50),
    disch_time_raw VARCHAR(50),
    death_time_raw VARCHAR(50),
    admission_type VARCHAR(250),
    admission_location VARCHAR(250),
    discharge_location VARCHAR(250),
    insurance VARCHAR(255),
    language VARCHAR(50),
    religion VARCHAR(250),
    marital_status VARCHAR(250),
    ethnicity VARCHAR(250),
    edreg_time_raw VARCHAR(50),
    edout_time_raw VARCHAR(50),
    diagnosis NVARCHAR(MAX),
    hospital_expire_flag NVARCHAR(MAX),
    has_chartevents_data NVARCHAR(MAX)
)
WITH (DATA_COMPRESSION = ROW);

BULK INSERT dbo.Admissions_Stage
FROM '/var/opt/SQL_Server_Docker/mimic/ADMISSIONS/ADMISSIONS_sorted.csv'
WITH (
    DATAFILETYPE = 'char',
    FIELDTERMINATOR = ',',
    ROWTERMINATOR = '0x0d0a',
    FIRSTROW = 2,
    FIELDQUOTE = '"',
    TABLOCK
);

WITH Converted AS (
    SELECT
        TRY_CONVERT(INT, TRY_CONVERT(NUMERIC(18, 0), NULLIF(hadm_id, ''))) AS admission_id,
        TRY_CONVERT(INT, TRY_CONVERT(NUMERIC(18, 0), NULLIF(subject_id, ''))) AS patient_id,
        TRY_CONVERT(DATETIME2(0), NULLIF(admit_time_raw, '')) AS admit_time,
        TRY_CONVERT(DATETIME2(0), NULLIF(disch_time_raw, '')) AS discharge_time,
        TRY_CONVERT(DATETIME2(0), NULLIF(death_time_raw, '')) AS death_time,
        NULLIF(LTRIM(RTRIM(admission_type)), '') AS admission_type,
        NULLIF(LTRIM(RTRIM(admission_location)), '') AS admission_location,
        NULLIF(LTRIM(RTRIM(discharge_location)), '') AS discharge_location,
        NULLIF(LTRIM(RTRIM(insurance)), '') AS insurance,
        NULLIF(LTRIM(RTRIM(marital_status)), '') AS marital_status,
        NULLIF(LTRIM(RTRIM(religion)), '') AS religion,
        NULLIF(LTRIM(RTRIM(ethnicity)), '') AS ethnicity
    FROM dbo.Admissions_Stage
)

INSERT INTO Admissions (
    admission_id,
    patient_id,
    admission_time,
    discharge_time,
    death_time,
    admission_type,
    admission_location,
    discharge_location,
    insurance,
    marital_status,
    religion,
    ethnicity
)
SELECT
    c.admission_id,
    c.patient_id,
    c.admit_time,
    CASE WHEN c.discharge_time IS NOT NULL AND c.admit_time IS NOT NULL AND c.discharge_time < c.admit_time THEN NULL ELSE c.discharge_time END,
    CASE WHEN c.death_time IS NOT NULL AND c.admit_time IS NOT NULL AND c.death_time < c.admit_time THEN NULL ELSE c.death_time END,
    c.admission_type,
    c.admission_location,
    c.discharge_location,
    c.insurance,
    c.marital_status,
    c.religion,
    c.ethnicity
FROM Converted AS c
WHERE c.admission_id IS NOT NULL
  AND c.patient_id IS NOT NULL
    AND c.admit_time IS NOT NULL
    AND EXISTS (
                SELECT 1
                FROM Patients AS p
                WHERE p.patient_id = c.patient_id
            )
        AND NOT EXISTS (
                    SELECT 1
                    FROM Admissions AS existing
                    WHERE existing.admission_id = c.admission_id
            );

DROP TABLE dbo.Admissions_Stage;
