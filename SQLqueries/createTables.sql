CREATE TABLE Patients(
    patient_id INT PRIMARY KEY,
    dob DATETIME2(0) NOT NULL,
    gender VARCHAR(20) NOT NULL CHECK (gender IN ('M', 'F')),
    is_dead VARCHAR(5)
);


CREATE TABLE Admissions (
    admission_id INT PRIMARY KEY,
    patient_id INT,
    admission_time DATETIME2(0) NOT NULL,
    discharge_time DATETIME2(0),
    death_time DATETIME2(0),
    admission_type VARCHAR(250) NOT NULL,
    admission_location VARCHAR(250),
    insurance VARCHAR(255),
    marital_status VARCHAR(250),
    religion VARCHAR(250),
    ethnicity VARCHAR(250),
    FOREIGN KEY (patient_id) REFERENCES Patients(patient_id),
    CONSTRAINT CK_Admissions_DischargeTime CHECK (discharge_time IS NULL OR discharge_time >= admission_time)
);


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
    FOREIGN KEY (admission_id) REFERENCES Admissions(admission_id),
    CONSTRAINT CK_ICUStays_OutTime CHECK (out_time IS NULL OR out_time >= in_time)
);


CREATE TABLE ICD_Diagnosis(
    ICD9_code VARCHAR(10) PRIMARY KEY,
    short_title VARCHAR(30) NOT NULL,
    long_title VARCHAR(255)
);


CREATE TABLE Diagnosis(
    diagnosis_id INT PRIMARY KEY,
    patient_id INT NOT NULL,
    admission_id INT,
    ICD9_code VARCHAR(10) NOT NULL,
    FOREIGN KEY (patient_id) REFERENCES Patients(patient_id),
    FOREIGN KEY (admission_id) REFERENCES Admissions(admission_id),
    FOREIGN KEY (ICD9_code) REFERENCES ICD_Diagnosis(ICD9_code)
);
