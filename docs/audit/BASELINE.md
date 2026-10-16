# Audit Baseline — CEP_Project

**Audit Date:** 2026-10-16  
**Auditor:** Automated Principal-Level Review  
**Git Baseline Commit:** `c73d342` — *"Initial production-ready wellness recommender"*  
**Working Directory Baseline:** Clean (no uncommitted changes before remediation)  

---

## 1. Repository Structure

```
CEP_Project/
├── .git/
├── .gitignore
├── README.md
├── package.json              (root — workspace orchestrator)
├── package-lock.json
│
├── backend/                  (Express + Mongoose)
│   ├── .env / .env.example
│   ├── package.json
│   ├── jest.config.js
│   ├── src/
│   │   ├── app.js            (Express application factory)
│   │   ├── server.js          (HTTP server startup & DB connection)
│   │   ├── config/            db.js, env.js
│   │   ├── controllers/       11 controllers (auth, dashboard, feedback, log, ml, etc.)
│   │   ├── middleware/        auth.js, errorHandler.js, rateLimiter.js, validation.js
│   │   ├── models/            8 Mongoose models + index.js
│   │   ├── routes/            11 route files
│   │   ├── rules/             ruleEngine.js + 5 rule modules (allergen, condition, metabolic)
│   │   ├── seed/              seed.js, seedData.js, dedupe.js
│   │   ├── services/          13 service modules (aiService, mlService, nutritionService, etc.)
│   │   ├── utils/             constants.js, errors.js, responses.js, security.js, validators.js
│   │   └── validators/        index.js (re-export)
│   └── tests/                 5 test files + setup.js
│
├── frontend/                 (React 18 + Vite)
│   ├── .env / .env.example
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   ├── dist/                 (built output — gitignored)
│   └── src/
│       ├── App.jsx
│       ├── main.jsx
│       ├── styles.css          (55 KB CSS design system)
│       ├── charts/             TrendChart.jsx
│       ├── components/         7 shared + 6 auth sub-components
│       ├── context/            AuthContext.jsx, ToastContext.jsx
│       ├── hooks/              useApi.js
│       ├── layouts/            AppLayout.jsx
│       ├── pages/              13 page components
│       └── services/           api.js
│
├── ai-ml/                    (Python 3.10+ / FastAPI / scikit-learn)
│   ├── .env / .env.example
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py             (FastAPI app)
│   │   ├── config.py
│   │   ├── ai/                 providers.py (stub)
│   │   ├── evaluation/         metrics.py
│   │   ├── features/           engineering.py
│   │   ├── models/             __init__.py
│   │   ├── prediction/         predictor.py
│   │   ├── preprocessing/      pipeline.py
│   │   ├── training/           train.py, dataset.py, retrain.py, evaluate.py
│   │   └── utils/              constants.py
│   ├── models/                 model.pkl (9.8 MB), random_forest_model.joblib (9.8 MB), feature_metadata.json
│   ├── data/                   sample_training_data.csv, README.md
│   └── tests/                  test_api.py, test_ml.py
│
├── scripts/
│   ├── start-ml.js             (Python virtualenv launcher)
│   └── test-ml.js              (Cross-platform pytest runner)
│
└── docs/
    ├── audit/                  (Full audit documentation suite)
    ├── architecture.md
    ├── api.md
    ├── database.md
    ├── ml.md
    └── viva.md
```

---

## 2. Technology Stack

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| **Root Workspace** | npm workspaces + concurrently | npm 10+, concurrently 9.1.2 | Orchestrates simultaneous frontend, backend, and ML services |
| **Frontend Framework** | React + Vite | React 18.3.1, Vite 5.4.11 | Single-Page Application client |
| **Frontend UI/Icons** | Vanilla CSS, Lucide React, Chart.js | chart.js 4.4.7, lucide-react 1.52.0 | Responsive styling, icons, and trend charts |
| **Frontend Routing** | React Router DOM | 6.28.0 | Declarative client-side route guards |
| **Backend Framework** | Node.js + Express | Express 4.21.2 | RESTful API server |
| **Database & ODM** | MongoDB + Mongoose | Mongoose 8.9.3 | Object Document Mapping, schema validation |
| **Auth & Session** | express-session + connect-mongo + bcryptjs | session 1.18.1, bcryptjs 2.4.3 | Stateful MongoDB session cookies & password hashing |
| **ML Inference Service** | Python + FastAPI + Uvicorn | FastAPI 0.115.6, Uvicorn 0.34.0 | High-performance Python microservice |
| **ML Modeling** | scikit-learn + joblib + pandas | scikit-learn 1.6.0, joblib 1.4.2 | 200-tree Random Forest classifier |
| **Testing (JS)** | Jest + Supertest + mongodb-memory-server | Jest 29.7.0, Supertest 7.0.0 | Unit and integration testing |
| **Testing (Py)** | pytest + httpx | pytest 8.3.4, httpx 0.28.1 | ML feature and API endpoint testing |

---

## 3. Application Entry Points

1. **Root Workspace Orchestrator:**
   - File: `package.json`
   - Command: `npm run dev`
   - Spawns: `concurrently` launching backend (`npm run dev --prefix backend`), frontend (`npm run dev --prefix frontend`), and ML service (`node scripts/start-ml.js`).

2. **Backend API Service:**
   - Server Entry: `backend/src/server.js` (establishes Mongoose DB connection, initializes HTTP listener on `env.port` and `env.host`).
   - App Factory: `backend/src/app.js` (`createApp()` configures middleware, security headers, sessions, routes, and error handling).

3. **Frontend Client Application:**
   - HTML Shell: `frontend/index.html` (mounts `#root`).
   - React Bootstrap: `frontend/src/main.jsx` (initializes React 18 root, ToastContext, and AuthContext).
   - Application Root: `frontend/src/App.jsx` (defines public and protected client routes).

4. **AI/ML Prediction Microservice:**
   - Python Entry: `ai-ml/app/main.py` (FastAPI app factory mounting `/health`, `/predict`, `/model/metadata`, and `/retrain`).
   - Virtualenv Launcher: `scripts/start-ml.js` (detects Windows/Unix Python virtualenv and launches Uvicorn on port 8000).

5. **Database Seed & Maintenance Utilities:**
   - Database Seed: `backend/src/seed/seed.js` (populates default foods, exercises, and admin accounts).
   - Database Deduplication: `backend/src/seed/dedupe.js` (MongoDB deduplication script).

---

## 4. Initial Test Results (Pre-Remediation Baseline)

### Backend (Jest)
```
Test Suites: 5 passed, 5 total
Tests:       41 passed, 41 total
Snapshots:   0 total
Time:        47.23 s
Exit:        Code 0 (forced exit — open handles warning)
```
*Baseline observation:* All 41 existing tests pass. However, Jest required `--forceExit` because the rate limiter periodic cleanup interval kept open async handles.

### Python (pytest)
- **Root execution (`python -m pytest -q`):** Failed during test collection due to system Python conflict (`Starlette 0.27.0` vs `httpx 0.28.1`).
- **Direct Virtualenv execution (`ai-ml/.venv/Scripts/pytest.exe -v`):** **9 passed, 0 failed in 12.79s** (7 tests in `test_ml.py`, 2 tests in `test_api.py`).
- *Baseline observation:* Root `npm run test:ml` needed a venv-aware launcher (`ISS-10`).

### Frontend (Vite)
- **Unit/Component Tests:** None present in `frontend/`.
- **Production Build (`npm run build --prefix frontend`):** **Succeeded in 4.06s** (1,950 modules transformed, 0 errors, output: JS 146.8 kB gzip, CSS 8.4 kB gzip).

---

## 5. Investigation of Visible Error (`scripts/dedupe-recommendations.js`)

**Finding:** The file `scripts/dedupe-recommendations.js` does **NOT exist** anywhere in the repository.

- **Investigation Evidence:**
  1. Full recursive search across workspace: 0 matches for `dedupe-recommendations`.
  2. Git history inspection across all 4 commits (`c73d342`, `7882ad6`, `e8576ac`, `faffad4`): No file was ever named `dedupe-recommendations.js`.
  3. Checked `package.json` scripts: No script references this path.
  4. Checked `scripts/` directory: Contains only `scripts/start-ml.js`.
- **Root Cause & Resolution:** The editor retained a stale reference to a hypothetical script name. The authentic deduplication script exists at `backend/src/seed/dedupe.js`. There is no missing-file defect in the repository.

---

## 6. Git History & Baseline Commit

```
c73d342 Initial production-ready wellness recommender
7882ad6 Updated with Medical Diagonises and LLM Api
e8576ac fix the ui
faffad4 Initial commit
```
Repository history consists of 4 commits. Working tree was clean at the start of the audit.

---

## 7. Environment & Secrets Baseline

- `.env.example` templates exist for root, `backend/`, `frontend/`, and `ai-ml/`.
- All `.env` files are correctly ignored by `.gitignore`.
- Static regex audit confirmed zero hardcoded API keys or plaintext credentials committed to Git.

---

## 8. Existing Issues Identified at Baseline (Pre-Remediation)

1. **Unmounted Rate Limiter (P1 / ISS-01):** `apiLimiter` defined but never attached to `/api` routes.
2. **Unthrottled Retraining (P1 / ISS-02):** `POST /api/ml/retrain` lacked rate limiting, allowing CPU starvation.
3. **Insecure Session Secret Fallback (P2 / ISS-03):** Allowed `'dev-only-change-me'` in production mode.
4. **Gemini Key in Query String (P2 / ISS-04):** Key passed via `?key=${apiKey}` URL parameter.
5. **Mongoose CastError 500 Crash (P2 / ISS-05):** Invalid ObjectIds caused unhandled 500 errors.
6. **Deleted User Null Dereference (P2 / ISS-06):** Stale sessions on deleted users threw 500 Internal Server Error.
7. **Localhost-Only Server Binding (P2 / ISS-07):** Express hardcoded to `127.0.0.1`, blocking container ingress.
8. **Missing Graceful Process Shutdown (P2 / ISS-08):** No `SIGTERM`/`SIGINT` handling for database connections.
9. **Model File Discrepancy (P2 / ISS-09):** Config pointed to gitignored `model.pkl` rather than tracked `random_forest_model.joblib`.
10. **Virtualenv Test Runner Gap (P2 / ISS-10):** Root `npm run test:ml` invoked system Python instead of `.venv`.
11. **Circular Workspace Dependencies (P3 / ISS-11):** Self-referential `"wellness-system": "file:.."` declared.
12. **Inconsistent Mongo URI in dedupe.js (P3 / ISS-12):** Checked `MONGODB_URI` instead of standard `MONGO_URI`.
13. **Rate Limiter Open Handles (P3 / ISS-14):** `setInterval` in `rateLimiter.js` prevented clean Jest exit.
14. **Unbounded Foods Query (P3 / ISS-15):** `/api/foods` executed unbounded `Food.find(filter)`.
15. **Missing CSP Header (P3 / ISS-13):** No Content-Security-Policy header defined.
16. **No Containerization or CI (P3 / ISS-16):** Absence of Dockerfile and GitHub Actions workflow.
