import sys
import os
import json
from datetime import datetime

# Add the current directory to sys.path to make imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from load_mongodb import MongoDBLoader

def check_patient_data(patient_id):
    loader = MongoDBLoader()
    if not loader.connect():
        print("Failed to connect to MongoDB.")
        return

    try:
        print(f"Fetching Patient {patient_id} from MongoDB...")
        if loader.db is None:
            print("Database connection is None")
            return
            
        patient = loader.db['patients'].find_one({'patient_id': patient_id})
        
        if not patient:
            print(f"Patient {patient_id} not found in MongoDB.")
            return

        # Helper to serialize datetime objects for JSON printing
        def json_serial(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return str(obj)

        print("\nPatient Document:")
        print("=" * 60)
        print(json.dumps(patient, indent=2, default=json_serial))
        print("=" * 60)
        
        # Specifically check admissions
        admissions = patient.get('admissions', [])
        print(f"\nAdmissions Array Length: {len(admissions)}")
        
        if admissions:
            print("\nFirst Admission Object Keys:")
            print(list(admissions[0].keys()))
            
            print("\nFirst Admission Content:")
            print(json.dumps(admissions[0], indent=2, default=json_serial))

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        loader.disconnect()

if __name__ == "__main__":
    # Check Patient 2 as we know they have 1 admission from the SQL check
    check_patient_data(2)
