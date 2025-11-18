"""
SQL Server data extraction module.
Extracts data from normalized SQL Server tables.
"""

import pyodbc
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from config import get_sql_connection_string, SQL_QUERIES

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SQLExtractor:
    """Handles extraction of data from SQL Server."""
    
    def __init__(self):
        """Initialize SQL Server connection."""
        self.conn_str = get_sql_connection_string()
        self.conn: Optional[pyodbc.Connection] = None
        self.cursor: Optional[pyodbc.Cursor] = None
        
    def connect(self) -> bool:
        """Establish connection to SQL Server."""
        try:
            self.conn = pyodbc.connect(self.conn_str)
            self.cursor = self.conn.cursor()
            logger.info("Successfully connected to SQL Server")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to SQL Server: {e}")
            return False
    
    def disconnect(self):
        """Close SQL Server connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("Disconnected from SQL Server")
    
    def fetch_all_patients(self) -> List[Dict[str, Any]]:
        """Fetch all patients from the database."""
        if not self.cursor:
            raise RuntimeError("Not connected to database. Call connect() first.")
        
        try:
            self.cursor.execute(SQL_QUERIES['patients'])
            columns = [column[0] for column in self.cursor.description]
            patients = []
            
            for row in self.cursor.fetchall():
                patient = dict(zip(columns, row))
                patients.append(patient)
            
            logger.info(f"Extracted {len(patients)} patients")
            return patients
            
        except Exception as e:
            logger.error(f"Error fetching patients: {e}")
            raise
    
    def fetch_admissions_for_patient(self, patient_id: int) -> List[Dict[str, Any]]:
        """Fetch all admissions for a specific patient."""
        if not self.cursor:
            raise RuntimeError("Not connected to database. Call connect() first.")
        
        try:
            self.cursor.execute(SQL_QUERIES['admissions'], patient_id)
            columns = [column[0] for column in self.cursor.description]
            admissions = []
            
            for row in self.cursor.fetchall():
                admission = dict(zip(columns, row))
                admissions.append(admission)
            
            return admissions
            
        except Exception as e:
            logger.error(f"Error fetching admissions for patient {patient_id}: {e}")
            raise
    
    def fetch_icu_stays_for_admission(self, admission_id: int) -> List[Dict[str, Any]]:
        """Fetch all ICU stays for a specific admission."""
        if not self.cursor:
            raise RuntimeError("Not connected to database. Call connect() first.")
        
        try:
            self.cursor.execute(SQL_QUERIES['icu_stays'], admission_id)
            columns = [column[0] for column in self.cursor.description]
            icu_stays = []
            
            for row in self.cursor.fetchall():
                icu_stay = dict(zip(columns, row))
                icu_stays.append(icu_stay)
            
            return icu_stays
            
        except Exception as e:
            logger.error(f"Error fetching ICU stays for admission {admission_id}: {e}")
            raise
    
    def fetch_diagnoses_for_admission(self, admission_id: int) -> List[Dict[str, Any]]:
        """Fetch all diagnoses for a specific admission."""
        if not self.cursor:
            raise RuntimeError("Not connected to database. Call connect() first.")
        
        try:
            self.cursor.execute(SQL_QUERIES['diagnoses'], admission_id)
            columns = [column[0] for column in self.cursor.description]
            diagnoses = []
            
            for row in self.cursor.fetchall():
                diagnosis = dict(zip(columns, row))
                diagnoses.append(diagnosis)
            
            return diagnoses
            
        except Exception as e:
            logger.error(f"Error fetching diagnoses for admission {admission_id}: {e}")
            raise
    
    def fetch_notes_for_admission(self, admission_id: int) -> List[Dict[str, Any]]:
        """Fetch all clinical notes for a specific admission."""
        if not self.cursor:
            raise RuntimeError("Not connected to database. Call connect() first.")
        
        try:
            self.cursor.execute(SQL_QUERIES['notes'], admission_id)
            columns = [column[0] for column in self.cursor.description]
            notes = []
            
            for row in self.cursor.fetchall():
                note = dict(zip(columns, row))
                notes.append(note)
            
            return notes
            
        except Exception as e:
            logger.error(f"Error fetching notes for admission {admission_id}: {e}")
            raise
    
    def get_table_counts(self) -> Dict[str, int]:
        """Get row counts for all tables."""
        if not self.cursor:
            raise RuntimeError("Not connected to database. Call connect() first.")
        
        counts = {}
        tables = ['Patients', 'Admissions', 'ICU_Stays', 'Diagnosis', 'Note_Events', 'ICD_Diagnosis']
        
        for table in tables:
            try:
                self.cursor.execute(f"SELECT COUNT(*) FROM {table}")
                result = self.cursor.fetchone()
                count = result[0] if result else 0
                counts[table] = count
                logger.info(f"Table {table}: {count:,} rows")
            except Exception as e:
                logger.error(f"Error counting {table}: {e}")
                counts[table] = -1
        
        return counts


if __name__ == "__main__":
    # Test extraction
    extractor = SQLExtractor()
    try:
        extractor.connect()
        
        # Get table counts
        print("\nTable Row Counts:")
        print("=" * 50)
        counts = extractor.get_table_counts()
        for table, count in counts.items():
            print(f"{table:20s}: {count:,}")
        
        # Test patient extraction
        print("\nExtracting sample patient data...")
        patients = extractor.fetch_all_patients()
        if patients:
            sample_patient = patients[0]
            print(f"\nSample Patient: {sample_patient['patient_id']}")
            
            admissions = extractor.fetch_admissions_for_patient(sample_patient['patient_id'])
            print(f"  - Admissions: {len(admissions)}")
            
            if admissions:
                sample_admission = admissions[0]
                icu_stays = extractor.fetch_icu_stays_for_admission(sample_admission['admission_id'])
                diagnoses = extractor.fetch_diagnoses_for_admission(sample_admission['admission_id'])
                notes = extractor.fetch_notes_for_admission(sample_admission['admission_id'])
                
                print(f"  - ICU Stays: {len(icu_stays)}")
                print(f"  - Diagnoses: {len(diagnoses)}")
                print(f"  - Notes: {len(notes)}")
        
    finally:
        extractor.disconnect()
