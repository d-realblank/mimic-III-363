SELECT
    s.patient_id,
    s.admission_id,
    COUNT(*) AS icu_stay_count
FROM ICU_Stays AS s
GROUP BY
    s.patient_id,
    s.admission_id
HAVING COUNT(*) > 1
ORDER BY s.patient_id, s.admission_id;