"""
MongoDB data loading module.
Handles insertion of transformed documents into MongoDB.
"""

import logging
from typing import Dict, Any, List, Optional
from pymongo import MongoClient, ASCENDING
from pymongo.errors import BulkWriteError, DuplicateKeyError
from config import MONGODB_CONFIG, MONGODB_INDEXES

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MongoDBLoader:
    """Handles loading data into MongoDB."""
    
    def __init__(self, connection_string: Optional[str] = None):
        """
        Initialize MongoDB connection.
        
        Args:
            connection_string: MongoDB connection string. If None, uses config.
        """
        if connection_string:
            self.connection_string = connection_string
        else:
            host = MONGODB_CONFIG['host']
            port = MONGODB_CONFIG['port']
            username = MONGODB_CONFIG.get('username')
            password = MONGODB_CONFIG.get('password')
            
            if username and password:
                self.connection_string = f"mongodb://{username}:{password}@{host}:{port}"
            else:
                self.connection_string = f"mongodb://{host}:{port}"
        
        self.db_name = MONGODB_CONFIG['database']
        self.client: Optional[MongoClient] = None
        self.db: Optional[Any] = None
    
    def connect(self) -> bool:
        """Establish MongoDB connection."""
        try:
            self.client = MongoClient(self.connection_string, serverSelectionTimeoutMS=5000)
            # Test connection
            self.client.admin.command('ping')
            self.db = self.client[self.db_name]
            logger.info(f"Connected to MongoDB database: {self.db_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False
    
    def disconnect(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    def create_indexes(self):
        """Create indexes for optimal query performance."""
        if self.db is None:
            raise RuntimeError("Not connected to MongoDB. Call connect() first.")
        
        try:
            # Patients collection indexes
            patients_col = self.db['patients']
            for index_spec in MONGODB_INDEXES['patients']:
                patients_col.create_index(
                    index_spec['keys'],
                    unique=index_spec.get('unique', False)
                )
                logger.info(f"Created index on patients: {index_spec['keys']}")
            
            # ICD reference collection indexes
            icd_col = self.db['icd_diagnoses']
            for index_spec in MONGODB_INDEXES['icd_diagnoses']:
                icd_col.create_index(
                    index_spec['keys'],
                    unique=index_spec.get('unique', False)
                )
                logger.info(f"Created index on icd_diagnoses: {index_spec['keys']}")
            
            logger.info("All indexes created successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
            return False
    
    def insert_patient_document(self, patient_doc: Dict[str, Any]) -> bool:
        """
        Insert single patient document.
        
        Args:
            patient_doc: Transformed patient document
            
        Returns:
            True if successful, False otherwise
        """
        if not self.db:
            raise RuntimeError("Not connected to MongoDB. Call connect() first.")
        
        try:
            result = self.db['patients'].replace_one(
                {'patient_id': patient_doc['patient_id']},
                patient_doc,
                upsert=True
            )
            if result.upserted_id:
                logger.debug(f"Inserted patient {patient_doc['patient_id']}")
            else:
                logger.debug(f"Updated patient {patient_doc['patient_id']}")
            return True
        except Exception as e:
            logger.error(f"Failed to insert patient {patient_doc.get('patient_id')}: {e}")
            return False
    
    def insert_patient_documents_batch(self, patient_docs: List[Dict[str, Any]]) -> int:
        """
        Insert batch of patient documents using bulk write.
        
        Args:
            patient_docs: List of transformed patient documents
            
        Returns:
            Number of successfully inserted documents
        """
        if not patient_docs:
            return 0
        
        if self.db is None:
            raise RuntimeError("Not connected to MongoDB. Call connect() first.")
        
        try:
            from pymongo import ReplaceOne
            
            operations = [
                ReplaceOne(
                    {'patient_id': doc['patient_id']},
                    doc,
                    upsert=True
                )
                for doc in patient_docs
            ]
            
            result = self.db['patients'].bulk_write(operations, ordered=False)
            inserted = result.upserted_count
            updated = result.modified_count
            logger.info(f"Batch insert: {inserted} inserted, {updated} updated")
            return inserted + updated
        except BulkWriteError as bwe:
            # Some may succeed even with errors
            write_errors = bwe.details.get('writeErrors', [])
            logger.error(f"Bulk write errors: {len(write_errors)} documents failed")
            for error in write_errors[:5]:  # Log first 5 errors
                logger.error(f"Error: {error}")
            return bwe.details.get('nInserted', 0) + bwe.details.get('nUpserted', 0)
        except Exception as e:
            logger.error(f"Failed batch insert: {e}")
            return 0
    
    def get_collection_count(self, collection_name: str) -> int:
        """Get document count for a collection."""
        if self.db is None:
            raise RuntimeError("Not connected to MongoDB. Call connect() first.")
        
        try:
            count = self.db[collection_name].count_documents({})
            return count
        except Exception as e:
            logger.error(f"Failed to count documents in {collection_name}: {e}")
            return -1
    
    def drop_collection(self, collection_name: str) -> bool:
        """Drop a collection (use with caution!)."""
        if self.db is None:
            raise RuntimeError("Not connected to MongoDB. Call connect() first.")
        
        try:
            self.db[collection_name].drop()
            logger.warning(f"Dropped collection: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to drop collection {collection_name}: {e}")
            return False
    
    def get_sample_documents(self, collection_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve sample documents from a collection."""
        if self.db is None:
            raise RuntimeError("Not connected to MongoDB. Call connect() first.")
        
        try:
            cursor = self.db[collection_name].find().limit(limit)
            return list(cursor)
        except Exception as e:
            logger.error(f"Failed to get sample documents from {collection_name}: {e}")
            return []


if __name__ == "__main__":
    # Test MongoDB connection and operations
    loader = MongoDBLoader()
    
    if loader.connect():
        print(f"Connected to MongoDB: {loader.db_name}")
        
        # Test getting counts
        patients_count = loader.get_collection_count('patients')
        icd_count = loader.get_collection_count('icd_diagnoses')
        print(f"Patients collection: {patients_count} documents")
        print(f"ICD Diagnoses collection: {icd_count} documents")
        
        # Test sample retrieval
        if patients_count > 0:
            samples = loader.get_sample_documents('patients', limit=1)
            print("\nSample patient document:")
            import json
            print(json.dumps(samples[0], indent=2, default=str))
        
        loader.disconnect()
    else:
        print("Failed to connect to MongoDB")
