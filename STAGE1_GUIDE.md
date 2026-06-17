# STAGE 1: Data Understanding with NLP & Recommendations
## Comprehensive Guide

---

## Table of Contents
1. [Overview](#overview)
2. [Components](#components)
3. [Getting Started](#getting-started)
4. [Detailed Workflows](#detailed-workflows)
5. [Advanced Usage](#advanced-usage)
6. [Troubleshooting](#troubleshooting)

---

## Overview

Stage 1 is the foundation phase of the EHR system, focused on:
- **Understanding** the clinical data structure and patterns
- **Extracting** clinical insights using NLP
- **Generating** evidence-based recommendations
- **Building** the knowledge base for later ML models

### Key Capabilities
- 📊 **Data Profiling** - Complete dataset analysis
- 🏷️ **Entity Extraction** - Clinical concepts identification
- 🔍 **Pattern Discovery** - Disease and medication patterns
- ⚠️ **Risk Stratification** - Patient risk assessment
- 💡 **Recommendations** - Actionable clinical suggestions

---

## Components

### 1. DataExploration Class

**File**: `stage1_data_understanding.py`

Provides comprehensive exploration of the EHR dataset.

#### Key Methods

```python
generate_full_report() -> Dict[str, Any]
```
Generates a complete exploration report including:
- Dataset overview (tables, rows, columns)
- Patient demographics
- Clinical patterns
- Data quality assessment
- Key findings

```python
save_report(filepath: str)
```
Export report to JSON format for further analysis.

#### Example Usage

```python
from stage1_data_understanding import DataExploration
from ehr import EHRSummarizer

# Initialize
ehr = EHRSummarizer('.')
exploration = DataExploration(ehr)

# Generate report
report = exploration.generate_full_report()

# Save for future reference
exploration.save_report('data_exploration_report.json')

# Access specific findings
print(report['dataset_overview'])
print(report['patient_demographics'])
print(report['clinical_patterns'])
```

---

### 2. ClinicalNLPAnalyzer Class

**File**: `nlp_analysis.py`

Advanced NLP processing for clinical text and concepts.

#### Key Capabilities

##### Entity Extraction
```python
entities = nlp.extract_clinical_entities(subject_id)
# Returns: {
#   'diagnoses': [...],
#   'procedures': [...],
#   'medications': [...],
#   'symptoms': [...],
#   'findings': [...]
# }
```

##### Severity Classification
```python
severity = nlp.classify_severity("Acute myocardial infarction")
# Returns: 'CRITICAL'
```

Classifications available:
- `CRITICAL` - Life-threatening conditions
- `MODERATE` - Significant conditions
- `MILD` - Minor conditions
- `UNKNOWN` - Unable to classify

##### Temporality Classification
```python
temporal = nlp.classify_temporality("Chronic heart failure")
# Returns: 'CHRONIC'
```

Classifications available:
- `ACUTE` - Sudden onset, recent
- `CHRONIC` - Long-standing, persistent
- `UNKNOWN` - Unable to classify

##### Disease Clustering
```python
clusters = nlp.find_disease_clusters()
# Returns: [
#   {
#     'diagnoses': ['250.00', '401.9'],
#     'descriptions': ['Diabetes', 'Hypertension'],
#     'co_occurrence_count': 2345,
#     'percentage': 15.3
#   },
#   ...
# ]
```

Identifies diseases that frequently co-occur in patients.

##### Drug Interactions
```python
interactions = nlp.extract_medication_interactions()
# Returns: [
#   {
#     'patient_id': 10006,
#     'drugs': ['Warfarin', 'Aspirin'],
#     'risk_level': 'HIGH',
#     'effect': 'Increased bleeding risk'
#   },
#   ...
# ]
```

Identifies potential medication interactions.

#### Complete Example

```python
from nlp_analysis import ClinicalNLPAnalyzer
from ehr import EHRSummarizer

ehr = EHRSummarizer('.')
nlp = ClinicalNLPAnalyzer(ehr)

# Print comprehensive NLP analysis
nlp.print_dataset_nlp_analysis()

# Patient-specific analysis
nlp.print_nlp_analysis(subject_id=10006)

# Extract specific entities
entities = nlp.extract_clinical_entities(10006)
print("Patient Diagnoses:")
for diagnosis in entities['diagnoses']:
    severity = nlp.classify_severity(diagnosis)
    print(f"  {diagnosis} [{severity}]")
```

---

### 3. RecommendationEngine Class

**File**: `stage1_data_understanding.py`

Generates clinical recommendations based on patient data.

#### Key Methods

##### Risk Factor Identification
```python
risk_factors = engine._identify_risk_factors(subject_id)
# Returns: [
#   {
#     'factor': 'Deceased Patient',
#     'severity': 'CRITICAL',
#     'description': 'Patient has expired during hospital stay'
#   },
#   ...
# ]
```

Identifies severity levels:
- `CRITICAL` - Immediate attention needed
- `HIGH` - Significant risk
- `MEDIUM` - Moderate concern
- `LOW` - Monitor

##### Medication Review
```python
med_review = engine._medication_review(subject_id)
# Returns: [
#   {
#     'type': 'POLYPHARMACY_ALERT',
#     'count': 15,
#     'recommendation': 'Consider deprescribing review',
#     'priority': 'MEDIUM'
#   },
#   ...
# ]
```

Review types:
- `POLYPHARMACY_ALERT` - Too many medications
- `DRUG_INTERACTION` - Potential interactions
- `CONTRAINDICATION` - Inappropriate combinations

##### Lab Monitoring Recommendations
```python
lab_recs = engine._lab_monitoring_recommendations(subject_id)
# Returns: [
#   {
#     'icd_code': '250',
#     'tests': 'HbA1c, Glucose',
#     'reason': 'Diabetes monitoring'
#   },
#   ...
# ]
```

Rule-based recommendations based on diagnosis codes.

##### Clinical Alerts
```python
alerts = engine._generate_clinical_alerts(subject_id)
# Returns: [
#   {
#     'alert_type': 'READMISSION_RISK',
#     'message': 'High readmission history',
#     'recommendation': 'Consider care coordination',
#     'severity': 'MEDIUM'
#   },
#   ...
# ]
```

##### Care Pathway Suggestions
```python
pathway = engine._suggest_care_pathway(subject_id)
# Returns: {
#   'primary_pathway': 'Medical Management',
#   'recommended_specialists': ['Endocrinology', 'Cardiology'],
#   'transition_planning': [...]
# }
```

#### Complete Example

```python
from stage1_data_understanding import RecommendationEngine
from ehr import EHRSummarizer

ehr = EHRSummarizer('.')
engine = RecommendationEngine(ehr)

# Get complete recommendations
recommendations = engine.get_patient_recommendations(10006)

# Print formatted recommendations
engine.print_recommendations(10006)

# Access specific recommendation components
print("Risk Factors:")
for risk in recommendations['risk_factors']:
    print(f"  [{risk['severity']}] {risk['factor']}")

print("\nMedication Review:")
for med_issue in recommendations['medication_review']:
    print(f"  {med_issue['recommendation']}")
```

---

### 4. Stage1Analysis Orchestrator

**File**: `stage1_data_understanding.py`

Main orchestrator class that coordinates all Stage 1 components.

#### Key Methods

```python
run_full_analysis() -> Dict[str, Any]
```
Executes complete Stage 1 analysis.

```python
analyze_specific_patient(subject_id: int)
```
Deep-dive analysis for a single patient.

#### Example Usage

```python
from stage1_data_understanding import Stage1Analysis

# Initialize
stage1 = Stage1Analysis('.')

# Run complete analysis
stage1.run_full_analysis()

# Analyze specific patient
stage1.analyze_specific_patient(10006)

# Access components
exploration_report = stage1.exploration.exploration_report
patient_recs = stage1.recommendations.get_patient_recommendations(10006)
```

---

## Getting Started

### Quick Start (5 minutes)

```python
from stage1_data_understanding import Stage1Analysis

# 1. Initialize
stage1 = Stage1Analysis('.')

# 2. Run analysis
stage1.run_full_analysis()

# 3. Get patient recommendations
stage1.recommendations.print_recommendations(10006)
```

### Step-by-Step Setup

```python
# Step 1: Load EHR data
from ehr import EHRSummarizer
ehr = EHRSummarizer('.')
print(f"Loaded {len(ehr.get_patient_list())} patients")

# Step 2: Explore data
from stage1_data_understanding import DataExploration
exploration = DataExploration(ehr)
report = exploration.generate_full_report()

# Step 3: Perform NLP analysis
from nlp_analysis import ClinicalNLPAnalyzer
nlp = ClinicalNLPAnalyzer(ehr)
nlp.print_dataset_nlp_analysis()

# Step 4: Get recommendations
from stage1_data_understanding import RecommendationEngine
engine = RecommendationEngine(ehr)
recommendations = engine.get_patient_recommendations(10006)
```

---

## Detailed Workflows

### Workflow 1: Understanding Patient Risk

```python
from stage1_data_understanding import Stage1Analysis

stage1 = Stage1Analysis('.')

# Get patient recommendations
patient_id = 10006
recommendations = stage1.recommendations.get_patient_recommendations(patient_id)

# Analyze risk factors
print("Risk Factors:")
for risk in recommendations['risk_factors']:
    print(f"  [{risk['severity']}] {risk['factor']}")
    print(f"    {risk['description']}")

# Check medication safety
print("\nMedication Safety:")
for med_rec in recommendations['medication_review']:
    print(f"  [{med_rec['priority']}] {med_rec['type']}")
    print(f"    {med_rec['recommendation']}")

# Review care pathway
print("\nCare Pathway:")
pathway = recommendations['care_pathway']
print(f"  Primary: {pathway['primary_pathway']}")
print(f"  Specialists: {', '.join(pathway['recommended_specialists'])}")
```

### Workflow 2: Analyzing Disease Patterns

```python
from nlp_analysis import ClinicalNLPAnalyzer
from stage1_data_understanding import Stage1Analysis

stage1 = Stage1Analysis('.')
nlp = ClinicalNLPAnalyzer(stage1.ehr)

# Find disease clusters
print("Disease Clusters:")
clusters = nlp.find_disease_clusters()
for cluster in clusters[:5]:
    print(f"\n{cluster['descriptions'][0]}")
    print(f"  + {cluster['descriptions'][1]}")
    print(f"  Co-occurrence: {cluster['percentage']:.1f}%")

# Find medication interactions
print("\n\nMedication Interactions:")
interactions = nlp.extract_medication_interactions()
if interactions:
    for interaction in interactions[:5]:
        print(f"{interaction['drugs'][0]} + {interaction['drugs'][1]}")
        print(f"  Risk: {interaction['risk_level']}")
        print(f"  Effect: {interaction['effect']}")
else:
    print("No interactions found")
```

### Workflow 3: Cohort Analysis

```python
from stage1_data_understanding import Stage1Analysis
from ehr_analytics import EHRAnalytics

stage1 = Stage1Analysis('.')
analytics = EHRAnalytics(stage1.ehr)

# Find patients with specific diagnosis
print("Finding patients with Diabetes (ICD-9: 250)...")
diabetes_patients = analytics.find_patients_by_diagnosis("250")
print(f"Found {len(diabetes_patients)} patients")

# Calculate cohort statistics
print(f"\nCohort Statistics:")
print(f"  Mortality Rate: {analytics.get_mortality_rate(diabetes_patients)*100:.1f}%")
print(f"  Average LOS: {analytics.get_average_los(diabetes_patients):.1f} days")
print(f"  Readmission Rate (30 days): {analytics.get_readmission_rate(30, diabetes_patients)*100:.1f}%")

# Find comorbidities
print(f"\nCommon Comorbidities:")
comorbidities = analytics.get_comorbidity_patterns("250", n=5)
for desc, count in comorbidities:
    print(f"  {count} patients - {desc}")
```

---

## Advanced Usage

### Custom Analysis Integration

```python
from stage1_data_understanding import DataExploration
from ehr import EHRSummarizer

class CustomAnalysis:
    def __init__(self, ehr_summarizer):
        self.ehr = ehr_summarizer
        self.data = ehr_summarizer.data
    
    def analyze_specialty_cohort(self, specialty: str):
        """Analyze patients by specialty"""
        if 'SERVICES' not in self.data:
            return {}
        
        services = self.data['SERVICES']
        specialty_patients = services[
            services['curr_service'] == specialty
        ]['subject_id'].unique()
        
        return {
            'specialty': specialty,
            'patient_count': len(specialty_patients),
            'patient_ids': specialty_patients.tolist()
        }

# Usage
ehr = EHRSummarizer('.')
custom = CustomAnalysis(ehr)
result = custom.analyze_specialty_cohort('CSURG')
print(f"{result['patient_count']} cardiac surgery patients")
```

### Export for Data Science

```python
import json
from stage1_data_understanding import Stage1Analysis

stage1 = Stage1Analysis('.')

# Generate and export complete report
report = stage1.exploration.generate_full_report()
stage1.exploration.save_report('stage1_output.json')

# Export NLP findings
nlp_findings = {
    'disease_clusters': stage1.recommendations.ehr.data['DIAGNOSES_ICD'].groupby('subject_id').size().describe().to_dict() if 'DIAGNOSES_ICD' in stage1.recommendations.ehr.data else {}
}

with open('nlp_findings.json', 'w') as f:
    json.dump(nlp_findings, f, indent=2, default=str)
```

---

## Troubleshooting

### Issue: "CSV file not found"
**Solution**: Ensure all CSV files are in the same directory as the script.

```python
from pathlib import Path
data_dir = Path('/path/to/csv/files')
stage1 = Stage1Analysis(str(data_dir))
```

### Issue: "KeyError" when accessing data
**Solution**: Check if the table exists in your dataset.

```python
# List available tables
ehr = EHRSummarizer('.')
print(ehr.data.keys())

# Check specific table
if 'NOTEEVENTS' not in ehr.data:
    print("NOTEEVENTS not available in this dataset")
```

### Issue: Memory error with large datasets
**Solution**: Filter data before analysis.

```python
# Analyze subset of patients
stage1 = Stage1Analysis('.')
sample_patients = stage1.ehr.get_patient_list()[:1000]

# Analyze sample
for patient_id in sample_patients[:10]:
    stage1.recommendations.print_recommendations(patient_id)
```

### Issue: Slow performance
**Solution**: Data is loaded once. If slow:
1. Reduce number of patients analyzed
2. Disable NLP clustering (expensive operation)
3. Increase system memory

```python
# Faster analysis without full clustering
from stage1_data_understanding import Stage1Analysis

stage1 = Stage1Analysis('.')
# Skip disease clustering
stage1.recommendations.get_patient_recommendations(10006)
```

---

## Next Steps

After stage 1 completes:

1. **Review the reports** generated by data exploration
2. **Identify key patterns** in clinical recommendations
3. **Plan Stage 2** - ML model development
4. **Prepare labeled data** for model training

See [ROADMAP.md](ROADMAP.md) for Stage 2 planning.

---

## Support

For issues or questions:
1. Check the main [README.md](README.md)
2. Review [examples.py](examples.py)
3. Check [ROADMAP.md](ROADMAP.md) for overall architecture

---

**Last Updated**: April 2024
**Version**: Stage 1 v1.0
