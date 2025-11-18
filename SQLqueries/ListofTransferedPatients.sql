SELECT DISTINCT
    p.patient_id
FROM Admissions AS a
JOIN Patients   AS p ON p.patient_id = a.patient_id
WHERE NULLIF(TRIM(a.admission_location), '') IS NOT NULL
  AND NULLIF(TRIM(a.discharge_location), '') IS NOT NULL
  AND UPPER(TRIM(a.admission_location))
      <> UPPER(TRIM(a.discharge_location))
  AND UPPER(a.discharge_location) NOT LIKE 'HOME%'
  AND UPPER(a.discharge_location) NOT LIKE 'DEAD%'