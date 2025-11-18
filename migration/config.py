"""
Configuration file for SQL Server to MongoDB migration.
Contains connection strings, credentials, and migration settings.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# SQL Server Configuration
SQL_SERVER_CONFIG = {
    'server': os.getenv('SQL_SERVER_HOST', 'localhost'),
    'port': os.getenv('SQL_SERVER_PORT', '1433'),
    'database': os.getenv('SQL_SERVER_DATABASE', 'master'),
    'username': os.getenv('SQL_SERVER_USERNAME', 'sa'),
    'password': os.getenv('SQL_SERVER_PASSWORD', 'YourStrong@Passw0rd'),
    'driver': '{ODBC Driver 18 for SQL Server}',
    'trust_server_certificate': 'yes'
}

# MongoDB Configuration
MONGODB_CONFIG = {
    'host': os.getenv('MONGODB_HOST', 'localhost'),
    'port': int(os.getenv('MONGODB_PORT', 27017)),
    'database': os.getenv('MONGODB_DATABASE', 'mimic_iii_nosql'),
    'username': os.getenv('MONGODB_USERNAME', ''),
    'password': os.getenv('MONGODB_PASSWORD', ''),
    'auth_source': os.getenv('MONGODB_AUTH_SOURCE', 'admin'),
    'tls': os.getenv('MONGODB_TLS', 'false').lower() == 'true',  # For MongoDB Atlas
    'srv': os.getenv('MONGODB_SRV', 'false').lower() == 'true'   # For mongodb+srv:// URIs
}

# Migration Settings
MIGRATION_CONFIG = {
    'batch_size': 100,  # Number of patients to process per batch
    'enable_logging': True,
    'log_file': 'migration.log',
    'validate_after_migration': True,
    'create_indexes': True,
    'drop_existing_collections': True  # WARNING: Set to False for incremental migration
}

# Collection Names
COLLECTIONS = {
    'patients': 'patients'
}

# SQL Queries
SQL_QUERIES = {
    'patients': """
        SELECT 
            patient_id,
            dob,
            gender,
            is_dead
        FROM Patients
        ORDER BY patient_id
    """,
    
    'admissions': """
        SELECT 
            admission_id,
            patient_id,
            admission_time,
            discharge_time,
            death_time,
            admission_type,
            admission_location,
            discharge_location,
            insurance,
            marital_status,
            religion,
            ethnicity
        FROM Admissions
        WHERE patient_id = ?
        ORDER BY admission_time
    """,
    
    'icu_stays': """
        SELECT 
            icu_id,
            patient_id,
            admission_id,
            in_time,
            out_time,
            first_care_unit,
            last_care_unit,
            first_ward_id,
            last_ward_id
        FROM ICU_Stays
        WHERE admission_id = ?
        ORDER BY in_time
    """,
    
    'diagnoses': """
        SELECT 
            d.diagnosis_id,
            d.ICD9_code,
            icd.short_title,
            icd.long_title
        FROM Diagnosis d
        INNER JOIN ICD_Diagnosis icd ON d.ICD9_code = icd.ICD9_code
        WHERE d.admission_id = ?
        ORDER BY d.diagnosis_id
    """,
    
    'notes': """
        SELECT 
            note_id,
            caregiver_id,
            create_date,
            create_time,
            category,
            description,
            text,
            is_error
        FROM Note_Events
        WHERE admission_id = ?
        ORDER BY note_id
    """
}

# Index Definitions for MongoDB
MONGODB_INDEXES = {
    'patients': [
        {'keys': [('patient_id', 1)], 'unique': True},
        {'keys': [('demographics.gender', 1)]},
        {'keys': [('admissions.admission_id', 1)]},
        {'keys': [('admissions.admission_time', 1)]},
        {'keys': [('admissions.diagnoses.icd9_code', 1)]}
    ]
}

def get_sql_connection_string():
    """Build SQL Server connection string."""
    cfg = SQL_SERVER_CONFIG
    conn_str = (
        f"DRIVER={cfg['driver']};"
        f"SERVER={cfg['server']},{cfg['port']};"
        f"DATABASE={cfg['database']};"
        f"UID={cfg['username']};"
        f"PWD={cfg['password']};"
        f"TrustServerCertificate={cfg['trust_server_certificate']};"
    )
    return conn_str

def get_mongodb_uri():
    """Build MongoDB connection URI with support for Atlas and remote servers."""
    cfg = MONGODB_CONFIG
    
    # Use mongodb+srv:// protocol for Atlas
    protocol = "mongodb+srv" if cfg.get('srv') else "mongodb"
    
    # Build authentication part
    if cfg['username'] and cfg['password']:
        auth = f"{cfg['username']}:{cfg['password']}@"
    else:
        auth = ""
    
    # Build host part (no port for SRV)
    if cfg.get('srv'):
        host_part = cfg['host']
    else:
        host_part = f"{cfg['host']}:{cfg['port']}"
    
    # Build query parameters
    query_params = []
    query_params.append(f"authSource={cfg['auth_source']}")
    
    if cfg.get('tls'):
        query_params.append("tls=true")
    
    query_string = "&".join(query_params) if query_params else ""
    
    # Build full URI
    if query_string:
        uri = f"{protocol}://{auth}{host_part}/{cfg['database']}?{query_string}"
    else:
        uri = f"{protocol}://{auth}{host_part}/{cfg['database']}"
    
    return uri
