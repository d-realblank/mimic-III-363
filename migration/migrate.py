"""
Main migration orchestrator.
Coordinates the extract-transform-load process.
"""

import logging
import sys
import argparse
from typing import Dict, Any, List
from datetime import datetime

from config import MIGRATION_CONFIG, get_sql_connection_string
from extract_sql_data import SQLExtractor
from transform_data import DataTransformer
from load_mongodb import MongoDBLoader

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class MigrationOrchestrator:
    """Orchestrates the complete migration process."""
    
    def __init__(self):
        self.sql_extractor = SQLExtractor()
        self.transformer = DataTransformer()
        self.mongo_loader = MongoDBLoader()
        self.batch_size = MIGRATION_CONFIG.get('batch_size', 100)
        self.stats = {
            'patients_processed': 0,
            'patients_migrated': 0,
            'icd_codes_migrated': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None
        }
    
    def connect_all(self) -> bool:
        """Establish all database connections."""
        try:
            if not self.sql_extractor.connect():
                logger.error("Failed to connect to SQL Server")
                return False
            
            if not self.mongo_loader.connect():
                logger.error("Failed to connect to MongoDB")
                return False
            
            logger.info("All database connections established")
            return True
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False
    
    def disconnect_all(self):
        """Close all database connections."""
        self.sql_extractor.disconnect()
        self.mongo_loader.disconnect()
        logger.info("All database connections closed")
    
    def migrate_patients(self) -> bool:
        """
        Migrate patient data with all related records.
        This is the main migration process.
        """
        logger.info("=" * 80)
        logger.info("Phase 1: Migrating Patient Data")
        logger.info("=" * 80)
        
        try:
            # Get all patients
            patients = self.sql_extractor.fetch_all_patients()
            total_patients = len(patients)
            logger.info(f"Found {total_patients} patients to migrate")
            
            patient_batch = []
            
            for idx, patient in enumerate(patients, 1):
                try:
                    patient_id = patient['patient_id']
                    
                    # Fetch all admissions for this patient
                    admissions = self.sql_extractor.fetch_admissions_for_patient(patient_id)
                    
                    # For each admission, fetch related data
                    transformed_admissions = []
                    for admission in admissions:
                        admission_id = admission['admission_id']
                        
                        # Fetch related records
                        icu_stays = self.sql_extractor.fetch_icu_stays_for_admission(admission_id)
                        diagnoses = self.sql_extractor.fetch_diagnoses_for_admission(admission_id)
                        notes = self.sql_extractor.fetch_notes_for_admission(admission_id)
                        
                        # Transform admission with all embedded data
                        transformed_admission = self.transformer.transform_admission(
                            admission, icu_stays, diagnoses, notes
                        )
                        transformed_admissions.append(transformed_admission)
                    
                    # Transform complete patient document
                    patient_doc = self.transformer.transform_patient_document(
                        patient, transformed_admissions
                    )
                    
                    patient_batch.append(patient_doc)
                    self.stats['patients_processed'] += 1
                    
                    # Process batch when full
                    if len(patient_batch) >= self.batch_size:
                        migrated = self.mongo_loader.insert_patient_documents_batch(patient_batch)
                        self.stats['patients_migrated'] += migrated
                        patient_batch = []
                        logger.info(
                            f"Progress: {idx}/{total_patients} patients "
                            f"({(idx/total_patients)*100:.1f}%) - "
                            f"{self.stats['patients_migrated']} migrated"
                        )
                    
                except Exception as e:
                    logger.error(f"Error processing patient {patient.get('patient_id')}: {e}")
                    self.stats['errors'] += 1
                    continue
            
            # Process remaining batch
            if patient_batch:
                migrated = self.mongo_loader.insert_patient_documents_batch(patient_batch)
                self.stats['patients_migrated'] += migrated
            
            logger.info(f"✓ Patient migration complete: {self.stats['patients_migrated']} patients migrated")
            return True
            
        except Exception as e:
            logger.error(f"Patient migration failed: {e}")
            return False
    
    def create_indexes(self) -> bool:
        """Create MongoDB indexes for performance."""
        logger.info("=" * 80)
        logger.info("Phase 2: Creating Indexes")
        logger.info("=" * 80)
        
        try:
            if self.mongo_loader.create_indexes():
                logger.info("✓ Indexes created successfully")
                return True
            else:
                logger.error("Index creation failed")
                return False
        except Exception as e:
            logger.error(f"Index creation error: {e}")
            return False
    
    def validate_migration(self) -> bool:
        """Basic validation of migration results."""
        logger.info("=" * 80)
        logger.info("Phase 4: Validation")
        logger.info("=" * 80)
        
        try:
            # Get counts from both databases
            sql_counts = self.sql_extractor.get_table_counts()
            mongo_patient_count = self.mongo_loader.get_collection_count('patients')
            mongo_icd_count = self.mongo_loader.get_collection_count('icd_diagnoses')
            
            logger.info("Row/Document Counts:")
            logger.info(f"  SQL Patients: {sql_counts.get('Patients', 0)}")
            logger.info(f"  MongoDB Patients: {mongo_patient_count}")
            logger.info(f"  SQL ICD Diagnoses: {sql_counts.get('ICD_Diagnosis', 0)}")
            logger.info(f"  MongoDB ICD Diagnoses: {mongo_icd_count}")
            
            # Basic validation
            patients_match = sql_counts.get('Patients', 0) == mongo_patient_count
            icd_match = sql_counts.get('ICD_Diagnosis', 0) == mongo_icd_count
            
            if patients_match and icd_match:
                logger.info("✓ Validation passed: counts match")
                return True
            else:
                logger.warning("⚠ Validation warning: counts do not match")
                if not patients_match:
                    logger.warning(f"  Patient count mismatch: SQL={sql_counts.get('Patients', 0)}, MongoDB={mongo_patient_count}")
                if not icd_match:
                    logger.warning(f"  ICD count mismatch: SQL={sql_counts.get('ICD_Diagnosis', 0)}, MongoDB={mongo_icd_count}")
                return False
                
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False
    
    def print_summary(self):
        """Print migration summary statistics."""
        duration = None
        if self.stats['start_time'] and self.stats['end_time']:
            duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        logger.info("=" * 80)
        logger.info("Migration Summary")
        logger.info("=" * 80)
        logger.info(f"Patients Processed: {self.stats['patients_processed']}")
        logger.info(f"Patients Migrated: {self.stats['patients_migrated']}")
        logger.info(f"ICD Codes Migrated: {self.stats['icd_codes_migrated']}")
        logger.info(f"Errors: {self.stats['errors']}")
        if duration:
            logger.info(f"Duration: {duration:.2f} seconds")
            if self.stats['patients_migrated'] > 0:
                rate = self.stats['patients_migrated'] / duration
                logger.info(f"Rate: {rate:.2f} patients/second")
        logger.info("=" * 80)
    
    def run(self, validate: bool = True) -> bool:
        """
        Execute the complete migration process.
        
        Args:
            validate: Whether to run validation after migration
            
        Returns:
            True if migration successful, False otherwise
        """
        self.stats['start_time'] = datetime.now()
        
        try:
            # Connect to databases
            if not self.connect_all():
                return False
            
            # Phase 1: Migrate patient data
            if not self.migrate_patients():
                logger.error("Patient data migration failed")
                return False
            
            # Phase 2: Create indexes
            if not self.create_indexes():
                logger.warning("Index creation failed, but migration data is intact")
            
            # Phase 3: Validation
            if validate:
                if not self.validate_migration():
                    logger.warning("Validation failed, please review manually")
            
            self.stats['end_time'] = datetime.now()
            self.print_summary()
            
            logger.info("✓ Migration completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False
        finally:
            self.disconnect_all()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Migrate MIMIC-III data from SQL Server to MongoDB')
    parser.add_argument('--no-validate', action='store_true', help='Skip validation after migration')
    
    args = parser.parse_args()
    
    orchestrator = MigrationOrchestrator()
    success = orchestrator.run(validate=not args.no_validate)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
