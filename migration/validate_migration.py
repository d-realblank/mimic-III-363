"""
Migration validation suite.
Validates data integrity and completeness after migration.
"""

import logging
import sys
from typing import Dict, Any, List, Tuple
from datetime import datetime

from config import get_sql_connection_string
from extract_sql_data import SQLExtractor
from load_mongodb import MongoDBLoader

logger = logging.getLogger(__name__)


class MigrationValidator:
    """Validates migration results."""
    
    def __init__(self):
        self.sql_extractor = SQLExtractor()
        self.mongo_loader = MongoDBLoader()
        self.validation_results = {
            'tests_passed': 0,
            'tests_failed': 0,
            'warnings': 0
        }
    
    def connect_all(self) -> bool:
        """Establish database connections."""
        if not self.sql_extractor.connect():
            logger.error("Failed to connect to SQL Server")
            return False
        if not self.mongo_loader.connect():
            logger.error("Failed to connect to MongoDB")
            return False
        return True
    
    def disconnect_all(self):
        """Close database connections."""
        self.sql_extractor.disconnect()
        self.mongo_loader.disconnect()
    
    def validate_row_counts(self) -> bool:
        """Validate that row counts match between SQL and MongoDB."""
        logger.info("=" * 80)
        logger.info("Test 1: Row Count Validation")
        logger.info("=" * 80)
        
        try:
            sql_counts = self.sql_extractor.get_table_counts()
            mongo_patient_count = self.mongo_loader.get_collection_count('patients')
            
            # Validate patient count matches
            match = sql_counts.get('Patients', 0) == mongo_patient_count
            status = "✓ PASS" if match else "✗ FAIL"
            logger.info(f"  Patients: SQL={sql_counts.get('Patients', 0)}, MongoDB={mongo_patient_count} [{status}]")
            
            if match:
                self.validation_results['tests_passed'] += 1
            else:
                self.validation_results['tests_failed'] += 1
            
            return match
            
        except Exception as e:
            logger.error(f"Row count validation error: {e}")
            self.validation_results['tests_failed'] += 1
            return False
    
    def validate_sample_patients(self, sample_size: int = 10) -> bool:
        """
        Validate a sample of patient records by comparing SQL vs MongoDB.
        
        Args:
            sample_size: Number of random patients to validate
        """
        logger.info("=" * 80)
        logger.info(f"Test 2: Sample Patient Validation (n={sample_size})")
        logger.info("=" * 80)
        
        try:
            # Get sample patient IDs from SQL
            patients = self.sql_extractor.fetch_all_patients()
            if not patients:
                logger.error("No patients found in SQL Server")
                self.validation_results['tests_failed'] += 1
                return False
            
            # Take first N patients (or random sample if preferred)
            sample_patients = patients[:sample_size]
            
            mismatches = 0
            for patient in sample_patients:
                patient_id = patient['patient_id']
                
                # Fetch from MongoDB
                if self.mongo_loader.db is None:
                    raise RuntimeError("MongoDB not connected")
                mongo_doc = self.mongo_loader.db['patients'].find_one({'patient_id': patient_id})
                
                if not mongo_doc:
                    logger.error(f"  Patient {patient_id} not found in MongoDB")
                    mismatches += 1
                    continue
                
                # Compare basic demographics
                sql_gender = patient.get('gender')
                mongo_gender = mongo_doc.get('demographics', {}).get('gender')
                
                if sql_gender != mongo_gender:
                    logger.error(
                        f"  Patient {patient_id} gender mismatch: "
                        f"SQL={sql_gender}, MongoDB={mongo_gender}"
                    )
                    mismatches += 1
                    continue
                
                # Count admissions
                sql_admissions = self.sql_extractor.fetch_admissions_for_patient(patient_id)
                mongo_admissions = mongo_doc.get('admissions', [])
                
                if len(sql_admissions) != len(mongo_admissions):
                    logger.warning(
                        f"  Patient {patient_id} admission count mismatch: "
                        f"SQL={len(sql_admissions)}, MongoDB={len(mongo_admissions)}"
                    )
                    self.validation_results['warnings'] += 1
                else:
                    logger.info(f"  ✓ Patient {patient_id}: demographics and admission count match")
            
            if mismatches == 0:
                logger.info(f"✓ Sample validation passed: all {sample_size} patients verified")
                self.validation_results['tests_passed'] += 1
                return True
            else:
                logger.error(f"✗ Sample validation failed: {mismatches} mismatches found")
                self.validation_results['tests_failed'] += 1
                return False
                
        except Exception as e:
            logger.error(f"Sample validation error: {e}")
            self.validation_results['tests_failed'] += 1
            return False
    
    def validate_embedded_data(self) -> bool:
        """
        Validate that embedded data (admissions, diagnoses, etc.) counts match.
        """
        logger.info("=" * 80)
        logger.info("Test 3: Embedded Data Validation")
        logger.info("=" * 80)
        
        try:
            sql_counts = self.sql_extractor.get_table_counts()
            
            # Count embedded admissions in MongoDB
            if self.mongo_loader.db is None:
                raise RuntimeError("MongoDB not connected")
            
            pipeline = [
                {'$unwind': '$admissions'},
                {'$count': 'total'}
            ]
            result = list(self.mongo_loader.db['patients'].aggregate(pipeline))
            mongo_admission_count = result[0]['total'] if result else 0
            
            sql_admission_count = sql_counts.get('Admissions', 0)
            
            logger.info(f"  Admissions: SQL={sql_admission_count}, MongoDB={mongo_admission_count}")
            
            if sql_admission_count == mongo_admission_count:
                logger.info("✓ Embedded admissions count matches")
                self.validation_results['tests_passed'] += 1
                return True
            else:
                logger.error(f"✗ Admission count mismatch: difference of {abs(sql_admission_count - mongo_admission_count)}")
                self.validation_results['tests_failed'] += 1
                return False
                
        except Exception as e:
            logger.error(f"Embedded data validation error: {e}")
            self.validation_results['tests_failed'] += 1
            return False
    
    def validate_data_integrity(self) -> bool:
        """
        Validate data integrity constraints in MongoDB.
        """
        logger.info("=" * 80)
        logger.info("Test 4: Data Integrity Validation")
        logger.info("=" * 80)
        
        try:
            if self.mongo_loader.db is None:
                raise RuntimeError("MongoDB not connected")
            
            issues = 0
            
            # Check for patients with no patient_id
            null_patient_id = self.mongo_loader.db['patients'].count_documents({'patient_id': None})
            if null_patient_id > 0:
                logger.error(f"  Found {null_patient_id} patients with NULL patient_id")
                issues += 1
            else:
                logger.info("  ✓ No NULL patient_ids found")
            
            # Check for duplicate patient_ids
            pipeline = [
                {'$group': {'_id': '$patient_id', 'count': {'$sum': 1}}},
                {'$match': {'count': {'$gt': 1}}}
            ]
            duplicates = list(self.mongo_loader.db['patients'].aggregate(pipeline))
            if duplicates:
                logger.error(f"  Found {len(duplicates)} duplicate patient_ids")
                issues += 1
            else:
                logger.info("  ✓ No duplicate patient_ids found")
            
            # Check for patients with no demographics
            no_demographics = self.mongo_loader.db['patients'].count_documents({'demographics': None})
            if no_demographics > 0:
                logger.warning(f"  Found {no_demographics} patients with NULL demographics")
                self.validation_results['warnings'] += 1
            else:
                logger.info("  ✓ All patients have demographics")
            
            if issues == 0:
                logger.info("✓ Data integrity checks passed")
                self.validation_results['tests_passed'] += 1
                return True
            else:
                logger.error(f"✗ Data integrity checks failed: {issues} issues found")
                self.validation_results['tests_failed'] += 1
                return False
                
        except Exception as e:
            logger.error(f"Data integrity validation error: {e}")
            self.validation_results['tests_failed'] += 1
            return False
    
    def validate_indexes(self) -> bool:
        """Validate that required indexes exist."""
        logger.info("=" * 80)
        logger.info("Test 5: Index Validation")
        logger.info("=" * 80)
        
        try:
            if self.mongo_loader.db is None:
                raise RuntimeError("MongoDB not connected")
            
            # Check patients collection indexes
            patients_indexes = list(self.mongo_loader.db['patients'].list_indexes())
            index_names = [idx['name'] for idx in patients_indexes]
            
            logger.info(f"  Patients collection indexes: {len(patients_indexes)}")
            for idx in patients_indexes:
                logger.info(f"    - {idx['name']}: {idx.get('key', {})}")
            
            # Check for patient_id unique index
            has_patient_id_index = any('patient_id' in str(idx.get('key', {})) for idx in patients_indexes)
            
            if has_patient_id_index:
                logger.info("✓ Required indexes exist")
                self.validation_results['tests_passed'] += 1
                return True
            else:
                logger.warning("⚠ patient_id index not found")
                self.validation_results['warnings'] += 1
                return False
                
        except Exception as e:
            logger.error(f"Index validation error: {e}")
            self.validation_results['tests_failed'] += 1
            return False
    
    def run_all_validations(self) -> bool:
        """Run all validation tests."""
        logger.info("=" * 80)
        logger.info("Starting Migration Validation Suite")
        logger.info("=" * 80)
        
        try:
            if not self.connect_all():
                return False
            
            # Run all tests
            self.validate_row_counts()
            self.validate_sample_patients(sample_size=10)
            self.validate_embedded_data()
            self.validate_data_integrity()
            self.validate_indexes()
            
            # Print summary
            logger.info("=" * 80)
            logger.info("Validation Summary")
            logger.info("=" * 80)
            logger.info(f"Tests Passed: {self.validation_results['tests_passed']}")
            logger.info(f"Tests Failed: {self.validation_results['tests_failed']}")
            logger.info(f"Warnings: {self.validation_results['warnings']}")
            logger.info("=" * 80)
            
            all_passed = self.validation_results['tests_failed'] == 0
            if all_passed:
                logger.info("✓ All validation tests passed")
            else:
                logger.error("✗ Some validation tests failed")
            
            return all_passed
            
        except Exception as e:
            logger.error(f"Validation suite error: {e}")
            return False
        finally:
            self.disconnect_all()


def main():
    """Main entry point."""
    validator = MigrationValidator()
    success = validator.run_all_validations()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
