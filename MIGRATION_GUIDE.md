# MIMIC-III SQL to NoSQL Migration Guide

## Table of Contents
1. [Overview](#overview)
2. [Source Database Schema](#source-database-schema)
3. [Target NoSQL Design](#target-nosql-design)
4. [Migration Strategy](#migration-strategy)
5. [Prerequisites](#prerequisites)
6. [Migration Scripts](#migration-scripts)
7. [Validation Procedures](#validation-procedures)
8. [Rollback Plan](#rollback-plan)

---

## Overview

### Purpose
Migrate the MIMIC-III medical database from a relational SQL Server structure to a document-oriented NoSQL database (MongoDB) to demonstrate:
- Schema design transformation from normalized to document-oriented
- Handling nested/hierarchical medical records
- Performance differences between relational and NoSQL databases
- Document-based query patterns

### Why Document Database for Medical Data?

**Rationale for MongoDB Selection:**

Medical records are inherently hierarchical with variable-length relationships. A document database provides optimal alignment with this data structure compared to other NoSQL approaches:

**Document Database Advantages:**
- **Natural hierarchy representation:** Patient → Admissions → Diagnoses → Notes maps directly to nested documents
- **Single-query retrieval:** Complete patient history accessible without joins or multiple lookups
- **Schema flexibility:** Variable admission counts (1-10+) and optional fields handled natively without NULL proliferation
- **Read optimization:** Historical research workloads benefit from document co-location and single I/O operations
- **Aggregation capabilities:** Rich pipeline operations for complex analytics on nested data structures

**Alternative NoSQL Types Considered:**

- **Key-Value Stores (Redis, DynamoDB):** Insufficient query capabilities for nested medical data; would require application-level joins
- **Column-Family Stores (Cassandra, HBase):** Optimized for write-heavy time-series; over-engineered for read-focused historical analysis
- **Graph Databases (Neo4j):** Better suited for network relationships; unnecessary complexity for hierarchical parent-child structures

**Trade-offs Accepted:**
- Data duplication (ICD code titles repeated) exchanged for query performance
- No ACID transactions across patients (acceptable for immutable historical data)
- Larger individual document sizes (60KB average) vs. normalized storage efficiency

**Conclusion:** Document databases align with medical record structure, access patterns, and research query requirements, making MongoDB the optimal choice for this migration.

### Migration Scope
- **Source:** SQL Server with 6 normalized tables
- **Target:** MongoDB with 1 denormalized collection (patient-centric)
- **Data Volume:** 10,000 patients with associated admissions, diagnoses, ICU stays, and clinical notes
- **Local Results:** 10,000 patients, 12,911 admissions embedded, 572,366 total sub-documents
- **Atlas Deployment:** 8,518 patients (85% of data, limited by free tier 512MB quota)
- **Timeline:** ~5 minutes local migration, ~5 minutes Atlas upload

---

## Deployment Options

The migration scripts support multiple MongoDB deployment scenarios:

### Local Development (Default)
- **MongoDB:** localhost:27017 without authentication
- **Use Case:** Development, testing, initial migration
- **Configuration:** Default settings in `.env` file

### MongoDB Atlas (Cloud)
- **MongoDB:** Free M0 tier (512 MB storage limit)
- **Use Case:** Remote access for demonstration and testing
- **Configuration:** Set `MONGODB_TLS=true` and `MONGODB_SRV=true` in `.env`
- **Connection:** Uses `mongodb+srv://` protocol with TLS encryption
- **Actual Deployment:** 8,518 patients deployed (85% of dataset fits within free tier)

### Self-Hosted Remote Server
- **MongoDB:** Custom server deployment with authentication
- **Use Case:** Learning server configuration and deployment
- **Configuration:** Set host, username, password in `.env`
- **Connection:** Standard `mongodb://` protocol with optional TLS

**See REMOTE_MONGODB_DEPLOYMENT.md for detailed deployment instructions**

---

## Source Database Schema

### Current SQL Server Tables

#### 1. Patients
```sql
CREATE TABLE Patients(
    patient_id INT PRIMARY KEY,
    dob DATETIME2(0) NOT NULL,
    gender VARCHAR(20) NOT NULL,
    is_dead VARCHAR(5)
);
```

#### 2. Admissions
```sql
CREATE TABLE Admissions (
    admission_id INT PRIMARY KEY,
    patient_id INT,
    admission_time DATETIME2(0) NOT NULL,
    discharge_time DATETIME2(0),
    death_time DATETIME2(0),
    admission_type VARCHAR(250) NOT NULL,
    admission_location VARCHAR(250),
    discharge_location VARCHAR(250),
    insurance VARCHAR(255),
    marital_status VARCHAR(250),
    religion VARCHAR(250),
    ethnicity VARCHAR(250),
    FOREIGN KEY (patient_id) REFERENCES Patients(patient_id)
);
```

#### 3. ICU_Stays
```sql
CREATE TABLE ICU_Stays(
    icu_id INT PRIMARY KEY,
    patient_id INT,
    admission_id INT,
    in_time DATETIME2(0) NOT NULL,
    out_time DATETIME2(0),
    first_care_unit VARCHAR(50),
    last_care_unit VARCHAR(300),
    first_ward_id INT,
    last_ward_id INT,
    FOREIGN KEY (patient_id) REFERENCES Patients(patient_id),
    FOREIGN KEY (admission_id) REFERENCES Admissions(admission_id)
);
```

#### 4. ICD_Diagnosis
```sql
CREATE TABLE ICD_Diagnosis(
    ICD9_code VARCHAR(10) PRIMARY KEY,
    short_title VARCHAR(30) NOT NULL,
    long_title VARCHAR(255)
);
```

#### 5. Diagnosis
```sql
CREATE TABLE Diagnosis(
    diagnosis_id INT PRIMARY KEY,
    patient_id INT NOT NULL,
    admission_id INT,
    ICD9_code VARCHAR(10) NOT NULL,
    FOREIGN KEY (patient_id) REFERENCES Patients(patient_id),
    FOREIGN KEY (admission_id) REFERENCES Admissions(admission_id),
    FOREIGN KEY (ICD9_code) REFERENCES ICD_Diagnosis(ICD9_code)
);
```

#### 6. Note_Events
```sql
CREATE TABLE Note_Events(
    note_id INT PRIMARY KEY,
    patient_id INT NOT NULL,
    admission_id INT,
    caregiver_id INT,
    create_date DATETIME2(0) NOT NULL,
    create_time DATETIME2(0),
    category VARCHAR(50),
    description VARCHAR(300),
    text TEXT NOT NULL,
    is_error VARCHAR(5),
    FOREIGN KEY (patient_id) REFERENCES Patients(patient_id),
    FOREIGN KEY (admission_id) REFERENCES Admissions(admission_id)
);
```

### Relationships
- One-to-Many: Patients → Admissions
- One-to-Many: Admissions → ICU_Stays
- One-to-Many: Admissions → Diagnoses
- One-to-Many: Admissions → Note_Events
- Many-to-One: Diagnosis → ICD_Diagnosis (reference table)

---

## Target NoSQL Design

### MongoDB Collection Structure

We will denormalize the relational schema into **1 primary collection**:

#### Collection 1: `patients` (Main Document)
```javascript
{
  "_id": ObjectId("..."),
  "patient_id": 12345,
  "demographics": {
    "dob": ISODate("1980-05-15T00:00:00Z"),
    "gender": "M",
    "is_dead": false
  },
  "admissions": [
    {
      "admission_id": 163353,
      "admission_time": ISODate("2138-07-17T19:04:00Z"),
      "discharge_time": ISODate("2138-07-21T15:48:00Z"),
      "death_time": null,
      "admission_type": "NEWBORN",
      "admission_location": "PHYS REFERRAL/NORMAL DELI",
      "discharge_location": "HOME",
      "insurance": "Private",
      "marital_status": null,
      "religion": "NOT SPECIFIED",
      "ethnicity": "ASIAN",
      
      "icu_stays": [
        {
          "icu_id": 243653,
          "in_time": ISODate("2138-07-17T21:20:07Z"),
          "out_time": ISODate("2138-07-17T23:32:21Z"),
          "first_care_unit": "NICU",
          "last_care_unit": "NICU",
          "first_ward_id": 56,
          "last_ward_id": 56
        }
      ],
      
      "diagnoses": [
        {
          "diagnosis_id": 1,
          "icd9_code": "V3001",
          "short_title": "Single liveborn, born in hospital",
          "long_title": "Single liveborn, born in hospital, delivered without mention of cesarean section"
        }
      ],
      
      "notes": [
        {
          "note_id": 1678764,
          "caregiver_id": 16929,
          "create_date": ISODate("2138-07-17T22:51:00Z"),
          "create_time": ISODate("2138-07-17T23:12:00Z"),
          "category": "Nursing/other",
          "description": "Report",
          "text": "Neonatology Attending Triage Note...",
          "is_error": false
        }
      ]
    }
  ],
  
  "metadata": {
    "created_at": ISODate("2025-11-18T..."),
    "migrated_from": "sql_server",
    "version": "1.0"
  }
}
```

**Design Rationale:**
- **Patient-centric model:** All medical data is grouped under the patient document
- **Embedded arrays:** Admissions, ICU stays, diagnoses, and notes are embedded to eliminate joins
- **Fully denormalized:** True NoSQL pattern
- **Read-optimized:** All patient data accessible in a single document query
- **Rich metadata:** Tracking migration provenance and versioning

**Why Single Collection? Understanding Patient-Centric Design**

In relational databases, we had 6 normalized tables with foreign keys. In MongoDB, we have **1 collection**. This isn't simplification—it's optimization for our use case.

**Why No Separate Collections for Admissions, ICU Stays, or Diagnoses?**
1. **Access Pattern Analysis:** 
   - 90% of queries are patient-focused: "Show all data for patient X"
   - Medical research analyzes patient outcomes over time (longitudinal data)
   - Rarely query individual admissions without patient context
   
2. **Performance Benefits:**
   - **Single document read** vs. 6 table joins in SQL
   - All related data co-located on disk (better caching)
   - No network round-trips between collections
   
3. **Data Relationship Reality:**
   - Average 1.29 admissions per patient (12,911 ÷ 10,000)
   - ICU stays are always tied to specific admissions
   - Diagnoses don't exist independently of admissions
   - Notes are contextual to admissions
   
4. **Document Size Consideration:**
   - Average document size: ~60 KB (well within MongoDB's 16 MB limit)
   - Even patients with 10+ admissions stay under 200 KB
   - Small enough for efficient reads, no need to split

**Why No Separate ICD Diagnosis Reference Collection?**
- ICD-9 codes are **read-only historical data** (frozen since 2015)
- Code titles are small (~50-100 characters each)
- Always accessed together with diagnosis data, never independently
- Embedding eliminates 14,567 potential lookups across all diagnoses
- True NoSQL pattern: **embed data you access together**

**When Would Separate Collections Make Sense?**
- **High write frequency:** If patients got 100+ new admissions daily
- **Independent access:** If you frequently queried admissions without patient context
- **Large embedded data:** If notes were 10+ MB each (images, scans)
- **Many-to-many relationships:** If diagnoses were shared across patients
- **Real-time updates:** If admission data changed frequently post-creation

**Our Use Case (Historical Medical Research):**
- ✓ Read-heavy workload (no new data being added)
- ✓ Complete patient history needed for analysis
- ✓ Small-to-medium document sizes
- ✓ One-to-many relationships (perfect for embedding)
- ✓ Data queried together, never independently

**Result:** Patient-centric single collection is the optimal NoSQL design pattern for this dataset.

---

## Migration Strategy

### Phase 1: Pre-Migration Assessment
1. **Data Profiling**
   - Count records in each table
   - Identify NULL values and data quality issues
   - Document foreign key relationships
   - Measure database size

2. **Schema Mapping**
   - Map SQL columns to MongoDB fields
   - Define embedding vs. referencing strategy
   - Plan index requirements

3. **Environment Setup**
   - Install MongoDB
   - Configure connection strings
   - Set up Python migration environment

### Phase 2: Patient Data Migration (with Embedded ICD Details)
1. Extract patients with all related data
2. Join ICD diagnosis details directly into diagnosis records
3. Embed all data into patient documents

### Phase 3: Core Data Migration
1. Extract patient demographics
2. For each patient:
   - Fetch all admissions
   - For each admission:
     - Embed ICU stays
     - Embed diagnoses (with ICD details)
     - Embed clinical notes
3. Insert complete patient document into MongoDB

### Phase 4: Post-Migration Validation
1. Row count verification
2. Sample data spot checks
3. Query performance testing
4. Data integrity validation

### Phase 5: Deployment
1. Final data sync if needed
2. Update application connection string
3. Test queries and verify functionality

---

## Prerequisites

### Software Requirements
1. **Python 3.8+** (tested with Python 3.14.0)
2. **SQL Server 2022** (running on Docker or native installation)
3. **MongoDB 6.0+** (tested with MongoDB 8.2.2)
   - Local installation, or
   - MongoDB Atlas account, or
   - Remote MongoDB server with network access
4. **ODBC Driver 18 for SQL Server** (macOS: available via Homebrew)
5. **unixodbc** (macOS: `brew install unixodbc`)

### MongoDB Setup
```bash
# Install MongoDB (macOS via Homebrew)
brew tap mongodb/brew
brew install mongodb-community@7.0

# Start MongoDB service
brew services start mongodb-community@7.0

# Verify installation
mongosh --version
```

### Python Environment
```bash
# Create virtual environment
python3 -m venv migration_env
source migration_env/bin/activate

# Install dependencies
pip install pymongo pyodbc pandas python-dotenv
```

### Database Connection Configuration

**SQL Server:**
Ensure your SQL Server container is running and accessible:
```bash
docker ps | grep sqlserver
```

**MongoDB:**
Configure connection in `.env` file based on deployment type:

```env
# Local MongoDB (default)
MONGODB_HOST=localhost
MONGODB_PORT=27017
MONGODB_DATABASE=mimic_iii_nosql

# MongoDB Atlas (for cloud hosting)
# MONGODB_HOST=cluster0.xxxxx.mongodb.net
# MONGODB_USERNAME=your_username
# MONGODB_PASSWORD=your_password
# MONGODB_TLS=true
# MONGODB_SRV=true

# Remote self-hosted
# MONGODB_HOST=your-server.com
# MONGODB_USERNAME=mimic_user
# MONGODB_PASSWORD=your_password
```

**Note:** The migration scripts automatically detect the deployment type and build the appropriate connection URI

---

## Migration Scripts

All scripts are located in `/migration/`

### Script 1: Environment Configuration
**File:** `config.py`

### Script 2: SQL Server Extraction
**File:** `extract_sql_data.py`

### Script 3: Data Transformation
**File:** `transform_data.py`

### Script 4: MongoDB Loading
**File:** `load_mongodb.py`

### Script 5: Main Migration Orchestrator
**File:** `migrate.py`

### Script 6: Validation Suite
**File:** `validate_migration.py`

---

## Validation Procedures

### 1. Record Count Validation
Compare counts between SQL Server and MongoDB:
```python
# SQL Server counts (actual)
SELECT COUNT(*) FROM Patients;          -- 10,000
SELECT COUNT(*) FROM Admissions;        -- 12,911
SELECT COUNT(*) FROM ICU_Stays;         -- 13,419
SELECT COUNT(*) FROM Diagnosis;         -- 113,547 (embedded in patient documents)
SELECT COUNT(*) FROM Note_Events;       -- 432,489 (embedded in patient documents)

# MongoDB Local counts (actual)
db.patients.countDocuments({})                                         -- 10,000
db.patients.aggregate([{$unwind: "$admissions"}, {$count: "total"}])  -- 12,911

# MongoDB Atlas counts (actual - limited by 512 MB free tier)
db.patients.countDocuments({})                                         -- 8,518

# Validation script
python validate_migration.py  # Should show all tests passed (local)
```

### 2. Data Integrity Checks
- Verify no orphaned records
- Check for NULL/missing required fields
- Validate date ranges (e.g., discharge_time >= admission_time)

### 3. Sample Data Verification
Randomly select 100 patients and manually compare SQL vs MongoDB records

### 4. Query Performance Testing
Run common queries and compare performance:
- Fetch patient with all admissions
- Find patients with multiple ICU stays
- Retrieve diagnoses by ICD code

---

## Rollback Plan

### Scenario 1: Migration Failure During Execution
**Action:** Stop migration script, preserve SQL Server data (unchanged), drop incomplete MongoDB collections

### Scenario 2: Post-Migration Data Issues
**Action:** 
1. Keep SQL Server online as source of truth
2. Re-run migration with corrected transformation logic
3. Use incremental sync for new/updated records

### Scenario 3: Application Compatibility Issues
**Action:**
1. Revert application to SQL Server connection
2. Analyze MongoDB query patterns
3. Adjust schema or add computed fields

---

## Change Log

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2025-11-18 | 1.0 | Migration Team | Initial migration guide created |
| 2025-11-18 | 1.1 | Migration Team | Local migration completed successfully (10K patients) |
| 2025-11-18 | 1.2 | Migration Team | Added remote deployment support (Atlas, self-hosted) |

## Related Documentation

- **MIGRATION_IMPLEMENTATION_NOTES.md** - Complete implementation history with all fixes and actual results
- **REMOTE_MONGODB_DEPLOYMENT.md** - Step-by-step guide for deploying to MongoDB Atlas or remote servers
- **migration/README.md** - Quick start guide for running migration scripts

---

## Next Steps

### Initial Migration (Completed)
1. ✅ Review and approve migration plan
2. ✅ Execute pre-migration assessment scripts
3. ✅ Run migration in local environment
4. ✅ Validate migration results (6/6 tests passed)
5. ✅ Document all implementation changes

### Remote Deployment (Optional)
1. **Choose deployment target:**
   - MongoDB Atlas (recommended for cloud hosting)
   - Self-hosted remote server
   - See `REMOTE_MONGODB_DEPLOYMENT.md` for detailed instructions

2. **Export local database:**
   ```bash
   mongodump --db mimic_iii_nosql --out /tmp/backup
   ```

3. **Import to remote MongoDB:**
   - For Atlas: Use `mongorestore` with Atlas connection string
   - For self-hosted: Transfer backup and restore on remote server

4. **Update configuration:**
   - Modify `.env` with remote MongoDB credentials
   - Set `MONGODB_TLS=true` for Atlas
   - Set `MONGODB_SRV=true` for Atlas

5. **Run validation on remote database:**
   ```bash
   python validate_migration.py  # Should show 6/6 tests passed
   ```

6. **Test performance:**
   - Compare query response times
   - Verify index utilization
   - Test common query patterns

---

## Additional Resources

For questions or issues:
- Review the troubleshooting section in `MIGRATION_IMPLEMENTATION_NOTES.md`
- Check MongoDB documentation: https://docs.mongodb.com/
- Consult course materials and TAs for project-specific questions
