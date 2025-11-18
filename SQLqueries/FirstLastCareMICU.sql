SELECT DISTINCT
    s.patient_id
FROM ICU_Stays AS s
WHERE UPPER(TRIM(s.first_care_unit)) = 'MICU'
  AND UPPER(TRIM(s.last_care_unit))  = 'MICU';