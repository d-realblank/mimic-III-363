# MIMIC-III NoSQL Migration Scripts

This directory contains Python scripts for migrating MIMIC-III medical data from SQL Server to MongoDB.

## Overview

The migration transforms a normalized relational schema (6 tables with foreign keys) into a document-oriented NoSQL database with a patient-centric design:

- **SQL Server:** 6 normalized tables (Patients, Admissions, ICU_Stays, Diagnosis, ICD_Diagnosis, Note_Events)
- **MongoDB:** 2 collections (patients with embedded documents, icd_diagnoses reference data)

## Prerequisites

1. **Python 3.8+** (tested with Python 3.14)
2. **SQL Server 2022** (running and accessible, tested on Linux Docker)
3. **MongoDB 6.0+** (installed and running, tested with MongoDB 8.2)
4. **ODBC Driver 18 for SQL Server** (required for macOS/Linux)
5. **unixodbc** (macOS: `brew install unixodbc`)

### Install MongoDB

macOS:
```bash
brew install mongodb-community
brew services start mongodb-community
```

Linux:
```bash
# Follow MongoDB installation guide for your distribution
sudo systemctl start mongod
```

### Install ODBC Driver (if not already installed)

macOS:
```bash
brew install unixodbc
# Download and install Microsoft ODBC Driver 18 from Microsoft's website
```

## Installation

1. **Install ODBC Driver and dependencies:**
```bash
# macOS
brew install unixodbc
brew install --cask microsoft-odbc-driver-18-for-sql-server
```

2. **Create Python virtual environment:**
```bash
cd migration
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your actual database credentials
# Important: Use SQL_SERVER_PASSWORD (not SQL_PASSWORD)
#           Use SQL_SERVER_DATABASE (not SQL_DATABASE)
#           Use SQL_SERVER_USERNAME (not SQL_USERNAME)
```

5. **Configure VS Code Python interpreter:**
- Press `Cmd+Shift+P` (macOS) or `Ctrl+Shift+P` (Windows/Linux)
- Type "Python: Select Interpreter"
- Choose `./venv/bin/python` or the virtual environment path

## Configuration

Edit `.env` file with your actual database credentials:

```env
SQL_SERVER_HOST=localhost
SQL_SERVER_PORT=1433
SQL_SERVER_DATABASE=master
SQL_SERVER_USERNAME=sa
SQL_SERVER_PASSWORD=YourStrongPassword123!

MONGODB_HOST=localhost
MONGODB_PORT=27017
MONGODB_DATABASE=mimic_iii_nosql
```

## Migration Scripts

### `config.py`
Centralized configuration for database connections, SQL queries, and MongoDB indexes.

### `extract_sql_data.py`
Extracts data from SQL Server with proper relationship handling:
- Fetches patients, admissions, ICU stays, diagnoses, clinical notes
- Handles hierarchical relationships (patient → admissions → ICU/diagnoses/notes)

### `transform_data.py`
Transforms relational data into document structure:
- Converts SQL rows into MongoDB documents
- Handles data type conversions (DATETIME2 → ISODate, VARCHAR → boolean)
- Embeds related records as nested arrays

### `load_mongodb.py`
Loads transformed documents into MongoDB:
- Batch inserts for performance
- Upsert operations for idempotency
- Index creation for query optimization

### `migrate.py`
Main orchestrator coordinating the full migration:
- Extract → Transform → Load pipeline
- Progress tracking and error handling
- Batch processing for memory efficiency

### `validate_migration.py`
Comprehensive validation suite:
- Row count comparisons
- Sample data verification
- Data integrity checks
- Index validation

## Usage

### Full Migration

Run complete migration with validation:
```bash
python migrate.py
```

Run migration without validation:
```bash
python migrate.py --no-validate
```

### Partial Migration

Migrate only ICD reference data:
```bash
python migrate.py --icd-only
```

### Validation Only

Run validation suite after migration:
```bash
python validate_migration.py
```

### Testing Individual Components

Test SQL extraction:
```bash
python extract_sql_data.py
```

Test data transformation:
```bash
python transform_data.py
```

Test MongoDB loading:
```bash
python load_mongodb.py
```

## Migration Process

The migration follows this 4-phase process:

### Phase 1: ICD Reference Data
- Extracts all ICD-9 diagnosis codes from SQL Server
- Transforms into reference documents
- Loads into `icd_diagnoses` collection

### Phase 2: Patient Data
- Iterates through all patients
- For each patient:
  1. Fetches all admissions
  2. For each admission, fetches ICU stays, diagnoses, and clinical notes
  3. Transforms into hierarchical document structure
  4. Embeds all related data
- Batch inserts into `patients` collection

### Phase 3: Index Creation
- Creates indexes on `patient_id` (unique)
- Creates indexes on `icd9_code` (unique)
- Additional indexes for common query patterns

### Phase 4: Validation
- Compares row/document counts
- Validates sample patient records
- Checks embedded data counts
- Verifies data integrity constraints

## Monitoring

Migration progress is logged to:
- **Console:** Real-time progress updates
- **migration.log:** Detailed execution log

Monitor log file during migration:
```bash
tail -f migration.log
```

## Troubleshooting

### Connection Issues

**SQL Server connection fails:**
```bash
# Test ODBC connection
python -c "import pyodbc; print(pyodbc.drivers())"
# Ensure 'ODBC Driver 18 for SQL Server' is listed

# Find your Docker SQL Server password
docker ps --format "{{.ID}}\t{{.Image}}" | grep mssql | awk '{print $1}' | xargs -I {} docker inspect {} | grep -A 2 "SA_PASSWORD"
```

**MongoDB connection fails:**
```bash
# Check MongoDB is running
brew services list | grep mongodb  # macOS
sudo systemctl status mongod       # Linux
```

### Memory Issues

If processing large datasets causes memory issues, reduce batch size in `config.py`:
```python
MIGRATION_CONFIG = {
    'batch_size': 50,  # Reduced from 100
    ...
}
```

### Linter Errors After Installation

**Issue**: Import errors for `pyodbc` or `pymongo` despite successful installation

**Solution**:
1. Ensure VS Code is using the virtual environment interpreter
2. Reload VS Code window: `Cmd+Shift+P` → "Developer: Reload Window"
3. Check `.vscode/settings.json` has correct interpreter path:
   ```json
   {
     "python.defaultInterpreterPath": "${workspaceFolder}/migration/venv/bin/python"
   }
   ```

**Note**: Type checking warnings about `cursor` or `db` being `None` are expected and handled with runtime guards. These are not actual errors.

### Data Type Errors

Check `migration.log` for specific transformation errors. Common issues:
- Invalid date formats (handled with `TRY_CONVERT` in SQL)
- NULL handling (use `NULLIF` and safe conversions)
- MongoDB database object truthiness: Always use `if db is None` instead of `if not db`

## Rollback

If migration fails or produces incorrect results:

1. **Drop MongoDB collections:**
```bash
mongosh mimic_iii_nosql --eval "db.patients.drop(); db.icd_diagnoses.drop();"
```

2. **Re-run migration:**
```bash
python migrate.py
```

The migration is idempotent - it uses upsert operations, so it's safe to re-run.

## Performance

Actual performance (tested on Apple M1/M2):
- **14,567 ICD codes:** ~250ms (Phase 1)
- **10,000 patients:** ~5 minutes (Phase 2)
- **Rate:** 30-35 patients/second with embedded data
- **Total migration time:** ~5-6 minutes including validation

Factors affecting performance:
- Number of admissions per patient
- Number of clinical notes (largest data volume)
- Batch size configuration
- Network latency between databases
- Disk I/O speed

## Document Structure

### Patient Document Example (Actual Migrated Data)
```json
{
  "_id": ObjectId("691caa3a357dbf982f86b77e"),
  "patient_id": 2,
  "demographics": {
    "dob": ISODate("2138-07-17T00:00:00.000Z"),
    "gender": "M",
    "is_dead": false
  },
  "admissions": [
    {
      "admission_id": 163353,
      "admission_time": ISODate("2138-07-17T19:04:00.000Z"),
      "discharge_time": ISODate("2138-07-21T15:48:00.000Z"),
      "death_time": null,
      "admission_type": "NEWBORN",
      "admission_location": "PHYS REFERRAL/NORMAL DELI",
      "discharge_location": "HOME",
      "insurance": "Private",
      "icu_stays": [
        {
          "icu_id": 243653,
          "in_time": ISODate("2138-07-17T21:20:07.000Z"),
          "out_time": ISODate("2138-07-17T23:32:21.000Z"),
          "first_care_unit": "NICU",
          "last_care_unit": "NICU"
        }
      ],
      "diagnoses": [
        {
          "diagnosis_id": 1,
          "icd9_code": "V3001",
          "short_title": "Single lb in-hosp w cs",
          "long_title": "Single liveborn, born in hospital, delivered by cesarean section"
        }
      ],
      "notes": [
        {
          "note_id": 1678764,
          "category": "Nursing/other",
          "description": "Report",
          "text": "...",
          "is_error": false
        }
      ]
    }
  ],
  "metadata": {
    "created_at": ISODate("2025-11-18T12:17:43.334Z"),
    "migrated_from": "sql_server",
    "version": "1.0"
  }
}
```

### Migration Statistics (Actual Results)
- **Total Patients**: 10,000
- **Total ICD Codes**: 14,567
- **Total Admissions**: 12,911 (embedded)
- **Male Patients**: 5,615
- **Female Patients**: 4,385
- **Deceased Patients**: 3,761
- **Top Admission Type**: EMERGENCY (8,319)
- **Top ICU Unit**: MICU (4,217)

## Validation Results

After migration, run the validation suite to verify data integrity:

```bash
python validate_migration.py
```

**Expected Results (All Tests Pass):**
- Test 1: Row Count Validation - Patients and ICD codes match
- Test 2: Sample Patient Validation - 10 random patients verified
- Test 3: Embedded Data Validation - 12,911 admissions correctly embedded
- Test 4: Data Integrity Validation - No NULLs, no duplicates
- Test 5: Index Validation - 6 indexes created

**Validation Time**: ~2 seconds

## Additional Resources

- **Full Documentation:** See `MIGRATION_GUIDE.md`
- **Implementation Notes:** See `MIGRATION_IMPLEMENTATION_NOTES.md`
- **SQL Schema:** See `/SQLqueries/createTables.sql`
- **Import Scripts:** See `/SQLqueries/import*.sql` files

## Support

For issues or questions:
1. Check `/migration/migration.log` for detailed error messages
2. Review `MIGRATION_GUIDE.md` for troubleshooting steps
3. Verify database connections and credentials
4. Ensure all prerequisites are installed
