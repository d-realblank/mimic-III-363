import sys
import os

# Add the current directory to sys.path to make imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from extract_sql_data import SQLExtractor
from config import SQL_QUERIES

def get_patient_admissions():
    extractor = SQLExtractor()
    if not extractor.connect():
        print("Failed to connect to SQL Server.")
        return

    try:
        # 1. Get a sample patient
        print("Fetching a sample patient...")
        patients = extractor.fetch_all_patients()
        if not patients:
            print("No patients found.")
            return

        # Pick the first patient
        patient_id = patients[0]['patient_id']
        print(f"Selected Patient ID: {patient_id}")

        # 2. Get admissions for this patient
        print(f"\nFetching admissions for Patient {patient_id}...")
        
        # Show the SQL Query being used
        print("\nExecuting SQL Query:")
        print("-" * 40)
        print(SQL_QUERIES['admissions'].strip())
        print("-" * 40)
        print(f"With parameter: patient_id = {patient_id}")

        admissions = extractor.fetch_admissions_for_patient(patient_id)

        # 3. Display results
        print(f"\nFound {len(admissions)} admission(s):")
        for i, adm in enumerate(admissions, 1):
            print(f"\n[Admission {i}]")
            print(f"  Admission ID: {adm['admission_id']}")
            print(f"  Type: {adm['admission_type']}")
            print(f"  Time: {adm['admission_time']}")
            print(f"  Discharge: {adm['discharge_time']}")
            print(f"  Location: {adm['admission_location']}")
            print(f"  Diagnosis: {adm.get('diagnosis', 'N/A')}") # Diagnosis might be in a separate table/query usually

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        extractor.disconnect()

if __name__ == "__main__":
    get_patient_admissions()
