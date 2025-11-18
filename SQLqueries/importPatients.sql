IF OBJECT_ID('dbo.Patients_Stage', 'U') IS NOT NULL
    DROP TABLE dbo.Patients_Stage;

CREATE TABLE dbo.Patients_Stage (
    row_id INT,
    subject_id INT,
    gender VARCHAR(20),
    dob_raw VARCHAR(50),
    dod_raw VARCHAR(50) NULL,
    dod_hosp_raw VARCHAR(50) NULL,
    dod_ssn_raw VARCHAR(50) NULL,
    expire_flag TINYINT
);

BULK INSERT dbo.Patients_Stage
FROM '/var/opt/SQL_Server_Docker/mimic/PATIENTS/PATIENTS_sorted.csv'
WITH (
    DATAFILETYPE = 'char',
    FIRSTROW = 2,          -- skip header row
    FIELDTERMINATOR = ',',
    ROWTERMINATOR = '0x0a',
    TABLOCK
);

INSERT INTO Patients (patient_id, dob, gender, is_dead)
SELECT
    subject_id,
    TRY_CONVERT(DATETIME2(0), dob_raw),
    gender,
    CASE WHEN expire_flag = 1 THEN 'TRUE' ELSE 'FALSE' END
FROM dbo.Patients_Stage;

DROP TABLE dbo.Patients_Stage;