"""
Data transformation module.
Transforms SQL Server relational data into MongoDB document structure.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataTransformer:
    """Transforms relational data into document-oriented structure."""
    
    @staticmethod
    def clean_string(value: Optional[str]) -> Optional[str]:
        """Clean and normalize string values."""
        if value is None or value == '':
            return None
        return str(value).strip()
    
    @staticmethod
    def parse_boolean(value: Optional[str]) -> bool:
        """Convert string boolean to actual boolean."""
        if value is None:
            return False
        value_upper = str(value).upper().strip()
        return value_upper in ('TRUE', '1', 'Y', 'YES')
    
    @staticmethod
    def safe_int(value: Any) -> Optional[int]:
        """Safely convert value to int."""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def safe_datetime(value: Any) -> Optional[datetime]:
        """Safely convert value to datetime."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        return None
    
    def transform_patient_demographics(self, patient: Dict[str, Any]) -> Dict[str, Any]:
        """Transform patient basic information into demographics subdocument."""
        return {
            'dob': self.safe_datetime(patient.get('dob')),
            'gender': self.clean_string(patient.get('gender')),
            'is_dead': self.parse_boolean(patient.get('is_dead'))
        }
    
    def transform_icu_stay(self, icu_stay: Dict[str, Any]) -> Dict[str, Any]:
        """Transform ICU stay record."""
        return {
            'icu_id': self.safe_int(icu_stay.get('icu_id')),
            'in_time': self.safe_datetime(icu_stay.get('in_time')),
            'out_time': self.safe_datetime(icu_stay.get('out_time')),
            'first_care_unit': self.clean_string(icu_stay.get('first_care_unit')),
            'last_care_unit': self.clean_string(icu_stay.get('last_care_unit')),
            'first_ward_id': self.safe_int(icu_stay.get('first_ward_id')),
            'last_ward_id': self.safe_int(icu_stay.get('last_ward_id'))
        }
    
    def transform_diagnosis(self, diagnosis: Dict[str, Any]) -> Dict[str, Any]:
        """Transform diagnosis record with embedded ICD details."""
        return {
            'diagnosis_id': self.safe_int(diagnosis.get('diagnosis_id')),
            'icd9_code': self.clean_string(diagnosis.get('ICD9_code')),
            'short_title': self.clean_string(diagnosis.get('short_title')),
            'long_title': self.clean_string(diagnosis.get('long_title'))
        }
    
    def transform_note(self, note: Dict[str, Any]) -> Dict[str, Any]:
        """Transform clinical note record."""
        return {
            'note_id': self.safe_int(note.get('note_id')),
            'caregiver_id': self.safe_int(note.get('caregiver_id')),
            'create_date': self.safe_datetime(note.get('create_date')),
            'create_time': self.safe_datetime(note.get('create_time')),
            'category': self.clean_string(note.get('category')),
            'description': self.clean_string(note.get('description')),
            'text': self.clean_string(note.get('text')),
            'is_error': self.parse_boolean(note.get('is_error'))
        }
    
    def transform_admission(
        self,
        admission: Dict[str, Any],
        icu_stays: List[Dict[str, Any]],
        diagnoses: List[Dict[str, Any]],
        notes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Transform admission record with all embedded subdocuments.
        
        Args:
            admission: Base admission record
            icu_stays: List of ICU stay records for this admission
            diagnoses: List of diagnosis records for this admission
            notes: List of clinical notes for this admission
            
        Returns:
            Transformed admission document
        """
        return {
            'admission_id': self.safe_int(admission.get('admission_id')),
            'admission_time': self.safe_datetime(admission.get('admission_time')),
            'discharge_time': self.safe_datetime(admission.get('discharge_time')),
            'death_time': self.safe_datetime(admission.get('death_time')),
            'admission_type': self.clean_string(admission.get('admission_type')),
            'admission_location': self.clean_string(admission.get('admission_location')),
            'discharge_location': self.clean_string(admission.get('discharge_location')),
            'insurance': self.clean_string(admission.get('insurance')),
            'marital_status': self.clean_string(admission.get('marital_status')),
            'religion': self.clean_string(admission.get('religion')),
            'ethnicity': self.clean_string(admission.get('ethnicity')),
            
            # Embedded arrays
            'icu_stays': [self.transform_icu_stay(icu) for icu in icu_stays],
            'diagnoses': [self.transform_diagnosis(dx) for dx in diagnoses],
            'notes': [self.transform_note(note) for note in notes]
        }
    
    def transform_patient_document(
        self,
        patient: Dict[str, Any],
        admissions_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Transform complete patient record into MongoDB document.
        
        Args:
            patient: Base patient record
            admissions_data: List of admission records (already transformed with embedded data)
            
        Returns:
            Complete patient document ready for MongoDB insertion
        """
        return {
            'patient_id': self.safe_int(patient.get('patient_id')),
            'demographics': self.transform_patient_demographics(patient),
            'admissions': admissions_data,
            'metadata': {
                'created_at': datetime.now(),
                'migrated_from': 'sql_server',
                'version': '1.0'
            }
        }


if __name__ == "__main__":
    # Test transformation
    transformer = DataTransformer()
    
    # Sample patient data
    sample_patient = {
        'patient_id': 12345,
        'dob': datetime(1980, 5, 15),
        'gender': 'M',
        'is_dead': 'FALSE'
    }
    
    sample_admission = {
        'admission_id': 163353,
        'patient_id': 12345,
        'admission_time': datetime(2138, 7, 17, 19, 4, 0),
        'discharge_time': datetime(2138, 7, 21, 15, 48, 0),
        'death_time': None,
        'admission_type': 'NEWBORN',
        'admission_location': 'PHYS REFERRAL/NORMAL DELI',
        'discharge_location': 'HOME',
        'insurance': 'Private',
        'marital_status': None,
        'religion': 'NOT SPECIFIED',
        'ethnicity': 'ASIAN'
    }
    
    sample_icu = {
        'icu_id': 243653,
        'in_time': datetime(2138, 7, 17, 21, 20, 7),
        'out_time': datetime(2138, 7, 17, 23, 32, 21),
        'first_care_unit': 'NICU',
        'last_care_unit': 'NICU',
        'first_ward_id': 56,
        'last_ward_id': 56
    }
    
    # Transform
    transformed_admission = transformer.transform_admission(
        sample_admission,
        [sample_icu],
        [],
        []
    )
    
    transformed_patient = transformer.transform_patient_document(
        sample_patient,
        [transformed_admission]
    )
    
    print("Transformed Patient Document:")
    print("=" * 80)
    import json
    print(json.dumps(transformed_patient, indent=2, default=str))
