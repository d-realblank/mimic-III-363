IF OBJECT_ID('dbo.Diagnosis_Stage', 'U') IS NOT NULL
    DROP TABLE dbo.Diagnosis_Stage;

CREATE TABLE dbo.Diagnosis_Stage (
    row_id VARCHAR(20),
    subject_id VARCHAR(50),
    hadm_id VARCHAR(50),
    seq_num VARCHAR(50),
    icd9_code VARCHAR(20)
);

BULK INSERT dbo.Diagnosis_Stage
FROM '/var/opt/SQL_Server_Docker/mimic/DIAGNOSES_ICD/DIAGNOSES_ICD_sorted.csv'
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
        TRY_CONVERT(INT, TRY_CONVERT(NUMERIC(18, 0), NULLIF(row_id, ''))) AS diagnosis_id,
        TRY_CONVERT(INT, TRY_CONVERT(NUMERIC(18, 0), NULLIF(subject_id, ''))) AS patient_id,
        TRY_CONVERT(INT, TRY_CONVERT(NUMERIC(18, 0), NULLIF(hadm_id, ''))) AS admission_id,
        NULLIF(LTRIM(RTRIM(icd9_code)), '') AS icd9_code
    FROM dbo.Diagnosis_Stage
)

INSERT INTO Diagnosis (
    diagnosis_id,
    patient_id,
    admission_id,
    ICD9_code
)
SELECT
    c.diagnosis_id,
    c.patient_id,
    c.admission_id,
    c.icd9_code
FROM Converted AS c
WHERE c.icd9_code IS NOT NULL
  AND c.diagnosis_id IS NOT NULL
  AND c.patient_id IS NOT NULL
  AND c.admission_id IS NOT NULL
  AND EXISTS (
        SELECT 1
        FROM Admissions AS a
        WHERE a.admission_id = c.admission_id
    )
  AND EXISTS (
        SELECT 1
        FROM Patients AS p
        WHERE p.patient_id = c.patient_id
        )
    AND EXISTS (
                SELECT 1
                FROM ICD_Diagnosis AS d
                WHERE d.ICD9_code = c.icd9_code
        );

DROP TABLE dbo.Diagnosis_Stage;
