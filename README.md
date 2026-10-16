# AI-Based Personal Nutrition, Activity & Wellness Recommendation System

A final-year project that turns a user's profile and daily wellness logs into
personalised nutrition, activity and wellness recommendations using a **hybrid
engine**: deterministic safety rules, a Random Forest for personalisation, and
transparent content-based scoring.

> This application is for general wellness and educational purposes only. It is
> not a medical or clinical tool and does not provide diagnosis, treatment, or
> medical advice.

## Architecture

React (Vite) talks to a Node.js Express API. Express owns authentication,
health metrics, the rule engine, content-based ranking, and MongoDB persistence.
A separate Python FastAPI service hosts scikit-learn. Optional OpenAI / Gemini /
Llama can generate additional recommendations; output filters are not clinical validation.

See [docs/architecture.md](docs/architecture.md).

## Features

- Registration, login, session cookies, hashed passwords, per-user isolation
- Profile with validated lifestyle, preference and goal fields
- BMI, BMR (Mifflin-St Jeor), TDEE, calorie target, macros, water target
- Nutrition plan (breakfast / lunch / dinner / snacks) with a reason per food
- Allergy, vegetarian, vegan and dislike filters that ML/AI cannot override
- Daily activity suggestions and a 7-day plan with difficulty ceilings
- Wellness tips, logs, dashboard charts (7 / 30 / 90 days), engagement score
- Feedback that can feed a gated retraining workflow
- ML explanation page with graceful fallback when the Python service is down
- Optional AI assistant — the app is fully usable without an API key

## Technology

| Layer | Choice |
|---|---|
| Frontend | React 18, Vite, JavaScript/JSX, React Router, Chart.js |
| Backend | Node.js, Express, Mongoose |
| Database | MongoDB |
| ML | Python, FastAPI, scikit-learn RandomForestClassifier |
| Auth | express-session, connect-mongo, bcryptjs |

Python exists **only** under `ai-ml/`.

## Folder structure

```
wellness-system/
  frontend/          React + Vite
  backend/           Express + MongoDB
  ai-ml/             FastAPI Random Forest service
  docs/
```

## Ports

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend | http://localhost:5000 |
| ML | http://localhost:8000 |
| MongoDB | mongodb://127.0.0.1:27017/wellness_db |

## Setup

### Prerequisites

Node 18+, Python 3.10+, MongoDB 6+ running locally.

### 1. Install

```bash
cd wellness-system
npm install
npm run install:all
python3 -m venv ai-ml/.venv
source ai-ml/.venv/bin/activate
pip install -r ai-ml/requirements.txt
```

### 2. Environment

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env   # optional
cp ai-ml/.env.example ai-ml/.env
```

### 3. Seed MongoDB

```bash
npm run seed -- --demo-user
```

Demo login: `demo@wellness.local` / `Demo1234` (fictional).

### 4. Train the ML model (optional but recommended)

```bash
cd ai-ml
source .venv/bin/activate
python -m app.training.train --dataset data/cep_ml_features_20000.csv --benchmark ../CEP_Synthetic_Data_20000/cep_ml_llm_benchmark_cases_200.csv --output-dir models/cep-20k-v2 --seed 42
```

The dataset is a **student/demo synthetic set**, not medical data.
Use a new output directory per experiment. The verified candidate is already saved
under `ai-ml/models/cep-20k-v1/`; original model files are preserved. See
[the ML workflow](docs/ml.md) for Windows commands, activation, reports and the
blocked Gemini benchmark. Training endpoints now require explicit administrator
configuration, and automatic feedback promotion is disabled.

### 5. Run

```bash
npm run dev          # frontend + Express
npm run dev:ml       # FastAPI on port 8000
```

If the ML service is down, recommendations still work (`source: rules_only`).

## Tests

```bash
npm test             # Jest + Supertest (Express)
npm run test:ml      # pytest (FastAPI / sklearn)
npm run build        # frontend production build
```

## Documentation

- [Architecture](docs/architecture.md)
- [API](docs/api.md)
- [Database](docs/database.md)
- [ML](docs/ml.md)
- [Viva notes](docs/viva.md)

## Limitations

Not a diagnostic tool. Food macros are approximate demo values. The classifier
is trained on synthetic labels. External AI is optional and may be unavailable.
