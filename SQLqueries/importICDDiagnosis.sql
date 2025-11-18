IF OBJECT_ID('dbo.ICDDiagnosis_Stage', 'U') IS NOT NULL
    DROP TABLE dbo.ICDDiagnosis_Stage;

CREATE TABLE dbo.ICDDiagnosis_Stage (
    row_id VARCHAR(20),
    icd9_code VARCHAR(20),
    short_title NVARCHAR(255),
    long_title NVARCHAR(MAX)
);

DECLARE @bulkCommand NVARCHAR(MAX) = N'
    BULK INSERT dbo.ICDDiagnosis_Stage
    FROM ''/var/opt/SQL_Server_Docker/mimic/D_ICD_DIAGNOSES/D_ICD_DIAGNOSES.csv''
    WITH (
        DATAFILETYPE = ''char'',
        FIELDTERMINATOR = '','',
        ROWTERMINATOR = ''0x0a'',
        FIRSTROW = 2,
        FIELDQUOTE = ''"'',
        TABLOCK
    );';

EXEC sys.sp_executesql @bulkCommand;

INSERT INTO ICD_Diagnosis (
    ICD9_code,
    short_title,
    long_title
)
SELECT DISTINCT
    NULLIF(LTRIM(RTRIM(REPLACE(src.icd9_code, '"', ''))), ''),
    NULLIF(LTRIM(RTRIM(REPLACE(src.short_title, '"', ''))), ''),
    NULLIF(LTRIM(RTRIM(REPLACE(src.long_title, '"', ''))), '')
FROM dbo.ICDDiagnosis_Stage AS src
WHERE NULLIF(LTRIM(RTRIM(REPLACE(src.icd9_code, '"', ''))), '') IS NOT NULL
  AND NOT EXISTS (
        SELECT 1
        FROM ICD_Diagnosis AS target
        WHERE target.ICD9_code = NULLIF(LTRIM(RTRIM(REPLACE(src.icd9_code, '"', ''))), '')
    );

SELECT @@ROWCOUNT AS InsertedRows;

SELECT COUNT(*) AS LoadedRowCount
FROM dbo.ICDDiagnosis_Stage;

DROP TABLE dbo.ICDDiagnosis_Stage;
