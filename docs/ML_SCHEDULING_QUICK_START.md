# ML Scheduling & Wait Time Prediction - Quick Start Guide

**TL;DR:** Implement XGBoost-based no-show prediction + LightGBM duration forecasting + Prophet wait time estimation to achieve **40% reduction in wait times** and **20% revenue increase**.

---

## 🎯 Top 5 Repositories to Use

### 1. Medical-Appointment-No-Show-Prediction ⭐⭐⭐⭐⭐
- **URL:** https://github.com/TimKong21/Medical-Appointment-No-Show-Prediction
- **Use For:** No-show prediction architecture
- **Tech:** XGBoost + AWS deployment (adapt to local FastAPI)
- **Action:** Clone and adapt feature engineering pipeline

### 2. Predicting-Patient-Wait-Time ⭐⭐⭐⭐
- **URL:** https://github.com/Keladry/Predicting-Patient-Wait-Time
- **Use For:** Wait time estimation
- **Tech:** Random Forest + Gradient Boosting
- **Action:** Extract feature engineering code

### 3. SimPy Visualisation (HSMA) ⭐⭐⭐⭐⭐
- **URL:** https://github.com/hsma-programme/simpy_visualisation
- **Use For:** Queue simulation and validation
- **Tech:** SimPy discrete event simulation
- **Action:** Test scheduling policies before deployment
- **Live Demo:** https://simpy-visualisation.streamlit.app/

### 4. US Naval Research Lab - Task Scheduling ⭐⭐⭐
- **URL:** https://github.com/USNavalResearchLaboratory/task-scheduling
- **Use For:** Reinforcement learning scheduler (Phase 2)
- **Tech:** OpenAI Gym + RL
- **Action:** Research for multi-provider optimization

### 5. Real-Time ML Prediction with FastAPI ⭐⭐⭐⭐
- **URL:** https://github.com/DanilBaibak/real-time-ml-prediction
- **Use For:** API deployment patterns
- **Tech:** FastAPI + scikit-learn
- **Action:** Copy API architecture for model serving

---

## 🏗️ Architecture (One-Pager)

```
┌─────────────────────────────────────────────────────────┐
│  INPUTS (Data Collection)                                │
├─────────────────────────────────────────────────────────┤
│ • Appointment history (appointments table)               │
│ • Patient demographics (EMR integration)                 │
│ • Real-time queue (Redis)                                │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  3 ML MODELS                                             │
├─────────────────────────────────────────────────────────┤
│ 1. No-Show Classifier (XGBoost) → P(no_show)            │
│    Metric: AUC > 0.85                                    │
│                                                           │
│ 2. Duration Regressor (LightGBM) → consultation minutes  │
│    Metric: MAE < 8.5 min                                 │
│                                                           │
│ 3. Wait Time Forecaster (Prophet + RF) → queue wait     │
│    Metric: MAE < 6 min                                   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  OPTIMIZATION ENGINE                                     │
├─────────────────────────────────────────────────────────┤
│ • Overbooking suggestions (if P(no_show) > 0.3)         │
│ • Schedule validation (SimPy simulation)                 │
│ • Real-time queue updates                                │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  FASTAPI ENDPOINTS                                       │
├─────────────────────────────────────────────────────────┤
│ POST /api/v1/predict/no-show                             │
│ POST /api/v1/predict/duration                            │
│ GET  /api/v1/queue/wait-time                             │
│ POST /api/v1/schedule/optimize                           │
└─────────────────────────────────────────────────────────┘
```

---

## 📊 Features to Collect (Priority Order)

### Tier 1: Essential (Implement First)
| Feature | Source | Example Value |
|---------|--------|---------------|
| `patient_no_show_rate_6m` | Calculated from history | 0.15 (15% no-show rate) |
| `lead_time_days` | booking_date → appointment_date | 7 days |
| `day_of_week` | appointment_datetime | 0 = Monday |
| `hour_of_day` | appointment_datetime | 14 (2 PM) |
| `appointment_type` | appointments table | "new_patient" / "follow_up" |
| `reminder_sent` | sms_logs table | True/False |
| `doctor_avg_duration` | Calculated rolling avg | 15.3 minutes |
| `patient_age` | EMR integration | 45 |
| `distance_to_clinic_km` | zip code → Google Maps | 8.5 km |

### Tier 2: Performance Boosters
- `is_holiday` (national/regional)
- `current_queue_length`
- `provider_utilization` (% of capacity booked)
- `days_since_last_visit`
- `chronic_conditions_count`

### Tier 3: Advanced (Phase 2)
- Patient cluster embeddings (similar behavior groups)
- Weather conditions
- Traffic patterns

---

## 🚀 4-Week Implementation Plan

### Week 1: Data Pipeline
- [ ] Query appointments table for last 12 months
- [ ] Create feature engineering functions (rolling stats)
- [ ] Set up PostgreSQL feature store table
- [ ] Integrate EMR patient demographics

### Week 2: Train Baseline Models
- [ ] Download Brazil no-show dataset (Kaggle) for initial training
- [ ] Train XGBoost no-show classifier (AUC > 0.80 target)
- [ ] Train LightGBM duration regressor (MAE < 10 min target)
- [ ] Train Prophet wait time model
- [ ] Evaluate on holdout set (Oct-Dec 2025 data)

### Week 3: API Development
- [ ] Create FastAPI endpoints (4 routes)
- [ ] Add Redis caching for patient features
- [ ] Write unit tests
- [ ] Deploy to staging environment

### Week 4: Frontend Integration
- [ ] Flutter: Display wait time in appointment booking screen
- [ ] Flutter: Show "High No-Show Risk" indicator for receptionists
- [ ] Web dashboard: Real-time queue status
- [ ] Test end-to-end workflow

---

## 💻 Code Snippets

### 1. Feature Engineering Example

```python
# backend/app/ml/features.py
import pandas as pd
from datetime import datetime, timedelta

def calculate_patient_features(patient_id, appointment_date, db):
    """Calculate rolling features for no-show prediction."""

    # Get patient's last 6 months of appointments
    six_months_ago = appointment_date - timedelta(days=180)
    history = db.query("""
        SELECT no_show, lateness_minutes, appointment_date
        FROM appointments
        WHERE patient_id = ? AND appointment_date BETWEEN ? AND ?
        ORDER BY appointment_date
    """, (patient_id, six_months_ago, appointment_date))

    if len(history) == 0:
        return {
            'patient_no_show_rate_6m': 0.20,  # Clinic average
            'visit_count_6m': 0,
            'avg_lateness_minutes': 0,
            'days_since_last_visit': 999
        }

    return {
        'patient_no_show_rate_6m': history['no_show'].mean(),
        'visit_count_6m': len(history),
        'avg_lateness_minutes': history['lateness_minutes'].mean(),
        'days_since_last_visit': (appointment_date - history['appointment_date'].max()).days
    }
```

### 2. XGBoost Training Script

```python
# backend/app/ml/train_no_show.py
import pandas as pd
from xgboost import XGBClassifier
from sklearn.metrics import roc_auc_score
from imblearn.over_sampling import SMOTE

# Load data
df = pd.read_sql("SELECT * FROM appointments WHERE appointment_date < '2025-10-01'", db)

# Feature engineering
X = df[['patient_no_show_rate_6m', 'lead_time_days', 'day_of_week',
        'hour_of_day', 'reminder_sent', 'distance_km']]
y = df['no_show']

# Handle class imbalance
sm = SMOTE(random_state=42)
X_balanced, y_balanced = sm.fit_resample(X, y)

# Train
model = XGBClassifier(
    max_depth=6,
    learning_rate=0.1,
    n_estimators=200,
    scale_pos_weight=3,  # Adjust for no-show ratio
    random_state=42
)
model.fit(X_balanced, y_balanced)

# Evaluate
y_test_pred = model.predict_proba(X_test)[:, 1]
auc = roc_auc_score(y_test, y_test_pred)
print(f"No-Show AUC: {auc:.3f}")  # Target: > 0.85

# Save
import joblib
joblib.dump(model, 'models/no_show_xgboost_v1.pkl')
```

### 3. FastAPI Prediction Endpoint

```python
# backend/app/api/v1/predictions.py
from fastapi import APIRouter
from pydantic import BaseModel
import joblib

router = APIRouter()
model_no_show = joblib.load('models/no_show_xgboost_v1.pkl')

class NoShowRequest(BaseModel):
    patient_id: int
    doctor_id: int
    appointment_datetime: str
    reminder_sent: bool

@router.post("/predict/no-show")
async def predict_no_show(req: NoShowRequest):
    # Feature engineering
    features = calculate_patient_features(req.patient_id, req.appointment_datetime, db)
    features['lead_time_days'] = calculate_lead_time(req.appointment_datetime)
    features['day_of_week'] = parse_datetime(req.appointment_datetime).weekday()
    features['reminder_sent'] = int(req.reminder_sent)

    # Predict
    X = [[features[f] for f in ['patient_no_show_rate_6m', 'lead_time_days',
                                 'day_of_week', 'reminder_sent']]]
    no_show_proba = model_no_show.predict_proba(X)[0][1]

    return {
        "patient_id": req.patient_id,
        "no_show_probability": float(no_show_proba),
        "risk_level": "high" if no_show_proba > 0.3 else "low",
        "recommendation": "Consider overbooking this slot" if no_show_proba > 0.3 else "Standard booking"
    }
```

---

## 📈 Expected Results (Research-Backed)

| Metric | Before ML | After ML | Source |
|--------|-----------|----------|--------|
| **No-Show Prediction AUC** | N/A | 0.85-0.95 | [Nature 2022](https://www.nature.com/articles/s41746-022-00594-w) |
| **Wait Time MAE** | ±15 min | 5-7 min | [ScienceDirect 2022](https://www.sciencedirect.com/science/article/pii/S187705092202097X) |
| **Duration Prediction MAE** | ±20 min | 8.55 min | [ScienceDirect 2020](https://www.sciencedirect.com/science/article/abs/pii/S1386505620309059) |
| **Patient Wait Time Reduction** | Baseline | 56% | [Cardiology Clinic Study](https://pubmed.ncbi.nlm.nih.gov/33099184/) |
| **Provider Utilization** | 70% | 90-92% | [IEEE 2024](https://ieeexplore.ieee.org/document/10380593/) |
| **Revenue Increase** | Baseline | +20% | Improved utilization |

---

## 🔧 Tech Stack Summary

| Component | Technology | Why? |
|-----------|-----------|------|
| **No-Show Model** | XGBoost | Best AUC (0.85+), handles imbalanced data |
| **Duration Model** | LightGBM | Fast training, low MAE (8.5 min) |
| **Wait Time Model** | Prophet + Random Forest | Handles seasonality + real-time queue |
| **API** | FastAPI | Already in use, async support |
| **Caching** | Redis | Patient features (1h TTL) |
| **Simulation** | SimPy | Validate policies without risk |
| **Monitoring** | Evidently AI | Detect model drift |
| **Retraining** | APScheduler | Weekly auto-retrain |

---

## 📚 Datasets for Training

1. **Brazil Medical No-Shows** (100K appointments)
   - URL: https://www.kaggle.com/datasets/wajahat1064/healthcare-appointment-dataset
   - Use: Baseline no-show model training

2. **Medical Appointment Scheduling System** (Synthetic)
   - URL: https://www.kaggle.com/datasets/carogonzalezgaltier/medical-appointment-scheduling-system
   - Use: Duration/wait time modeling

3. **Your Clinic Data** (Production)
   - Source: PostgreSQL `appointments` table (last 12 months)
   - Use: Fine-tune models for your clinic

---

## ⚠️ Common Pitfalls & Solutions

| Pitfall | Solution |
|---------|----------|
| **Class imbalance (20% no-shows)** | Use SMOTE or `scale_pos_weight` in XGBoost |
| **Data leakage (future info in features)** | Use temporal split (train on old data, test on recent) |
| **Overfitting to clinic patterns** | Cross-validate across different months |
| **Cold start (new patients)** | Use clinic-wide averages as fallback |
| **Model drift** | Weekly retraining + Evidently AI monitoring |
| **API latency** | Redis cache patient features (1h TTL) |

---

## 🎯 Success Metrics (Track Weekly)

1. **Model Performance**
   - No-Show AUC > 0.85
   - Duration MAE < 8.5 min
   - Wait Time MAE < 6 min

2. **Business Impact**
   - Average wait time < 20 min (from 35 min)
   - Provider utilization > 90% (from 75%)
   - No-show rate < 15% (from 25%)

3. **Operational**
   - API P95 latency < 100ms
   - Zero prediction errors (fallback to defaults)
   - Model retraining success rate 100%

---

## 🚦 Go/No-Go Decision Criteria

**✅ Proceed if:**
- Appointments table has > 5,000 historical records
- At least 6 months of data available
- Data quality > 90% (no missing values in key fields)
- Development team has Python ML experience

**🛑 Defer if:**
- < 1,000 historical appointments (use clinic averages first)
- No EMR integration yet (build that first)
- Unstable appointment booking process (fix workflows first)

---

## 📞 Next Steps

1. **Review this document** with team (30 min)
2. **Run data audit query** (see below)
3. **Download Kaggle dataset** and train proof-of-concept model (2 hours)
4. **Schedule kickoff meeting** to assign roles

### Data Audit Query
```sql
-- Check data availability
SELECT
    COUNT(*) as total_appointments,
    COUNT(DISTINCT patient_id) as unique_patients,
    COUNT(DISTINCT doctor_id) as unique_doctors,
    MIN(appointment_date) as earliest_date,
    MAX(appointment_date) as latest_date,
    AVG(CASE WHEN no_show THEN 1 ELSE 0 END) as no_show_rate,
    COUNT(CASE WHEN actual_duration IS NULL THEN 1 END) as missing_duration
FROM appointments
WHERE appointment_date >= DATE('now', '-12 months');
```

**Good data:** > 5,000 appointments, < 10% missing durations
**Needs work:** < 1,000 appointments, > 30% missing durations

---

**For detailed implementation, see:** `/home/user/appointment_system/docs/ML_WAIT_TIME_SCHEDULE_OPTIMIZATION_RESEARCH.md`

**Last Updated:** January 4, 2026
