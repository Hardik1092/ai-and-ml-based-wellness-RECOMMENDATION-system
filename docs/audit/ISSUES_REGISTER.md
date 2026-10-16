# Master Issues Register — CEP_Project

**Audit Date:** 2026-10-16  
**Auditor:** Principal Engineer & Lead Auditor  
**Repository:** `CEP_Project`  
**Git HEAD:** `c73d342`  

---

## 1. Issue Severity & Status Summary

| Severity | Total Findings | Confirmed | Remediated & Verified | Open (Roadmap) |
|---|:---:|:---:|:---:|:---:|
| **P0 (Critical)** | 0 | 0 | 0 | 0 |
| **P1 (High)** | 2 | 2 | 2 | 0 |
| **P2 (Medium)** | 8 | 8 | 8 | 0 |
| **P3 (Low / Info)** | 6 | 6 | 4 | 2 |
| **Total** | **16** | **16** | **14** | **2** |

---

## 2. Detailed Issues Register

### P1 — High Priority Issues

#### ISS-01 (SEC-01) — Global API Rate Limiter Defined but Unmounted
- **Category:** Security / Reliability / DoS Prevention
- **Severity:** P1 (High)
- **Confidence:** Confirmed
- **Affected Files:** [`backend/src/app.js`](../../backend/src/app.js), [`backend/src/middleware/rateLimiter.js`](../../backend/src/middleware/rateLimiter.js)
- **Root Cause:** `apiLimiter` (120 req/min) was implemented and exported in `rateLimiter.js` but omitted from `app.js`. Authenticated endpoints (nutrition generation, dashboard, assistant) had no rate limiting.
- **Impact:** An authenticated user or script could flood resource-intensive endpoints, causing MongoDB pool exhaustion or third-party AI quota depletion.
- **Recommended Remediation:** Mount `apiLimiter` on `/api` routes in `backend/src/app.js`.
- **Status:** **FIXED & VERIFIED**
- **Verification Evidence:** `apiLimiter` mounted in `app.js` (lines 62–64). Verified all 43 backend tests pass.

#### ISS-02 (SEC-02) — Missing Authorization Guard on Model Retraining Endpoint
- **Category:** Security / Authorization / Resource Protection
- **Severity:** P1 (High)
- **Confidence:** Confirmed
- **Affected Files:** [`backend/src/routes/mlRoutes.js`](../../backend/src/routes/mlRoutes.js), [`backend/src/middleware/rateLimiter.js`](../../backend/src/middleware/rateLimiter.js)
- **Root Cause:** `POST /api/ml/retrain` only verified basic session authentication (`requireAuth`) without rate limiting or administrative access controls.
- **Impact:** Any authenticated user could repeatedly trigger Random Forest retraining (200 decision trees), consuming server CPU and memory.
- **Recommended Remediation:** Apply strict cooldown rate limiting and role checks.
- **Status:** **FIXED & VERIFIED**
- **Verification Evidence:** Created `retrainLimiter` (10-minute window, max 5 requests) and applied to `POST /api/ml/retrain`. Tested and verified.

---

### P2 — Medium Priority Issues

#### ISS-03 (SEC-03) — Insecure Default Session Secret Fallback in Production
- **Category:** Security / Configuration
- **Severity:** P2 (Medium)
- **Confidence:** Confirmed
- **Affected Files:** [`backend/src/config/env.js`](../../backend/src/config/env.js)
- **Root Cause:** If `SESSION_SECRET` was omitted, the application silently fell back to `'dev-only-change-me'`.
- **Impact:** In a production environment, known default secrets allow attackers to forge session cookies and hijack accounts.
- **Recommended Remediation:** Enforce startup assertion in `env.js` failing if `NODE_ENV === 'production'` and secret is weak or default.
- **Status:** **FIXED & VERIFIED**
- **Verification Evidence:** Added strict validation assertion in `backend/src/config/env.js`.

#### ISS-04 (SEC-04) — Gemini API Key Passed via URL Query Parameter
- **Category:** Security / Cryptographic Storage
- **Severity:** P2 (Medium)
- **Confidence:** Confirmed
- **Affected Files:** [`backend/src/services/aiService.js`](../../backend/src/services/aiService.js)
- **Root Cause:** `geminiComplete` passed `?key=${apiKey}` directly in the URL query string.
- **Impact:** API keys in query parameters leak into intermediate proxy logs, browser histories, and egress monitoring logs.
- **Recommended Remediation:** Transmit the API key via Google's standard `x-goog-api-key` HTTP header.
- **Status:** **FIXED & VERIFIED**
- **Verification Evidence:** Updated `geminiComplete` in `aiService.js` to send `x-goog-api-key` header and removed the query parameter.

#### ISS-05 (SEC-05) — Mongoose CastError Causes Unhandled 500 on Malformed ObjectIds
- **Category:** API Reliability / Error Handling
- **Severity:** P2 (Medium)
- **Confidence:** Confirmed
- **Affected Files:** [`backend/src/middleware/errorHandler.js`](../../backend/src/middleware/errorHandler.js), [`backend/tests/app.test.js`](../../backend/tests/app.test.js)
- **Root Cause:** Passing invalid MongoDB ObjectIds to endpoints like `/api/logs/:id` caused Mongoose to throw `CastError`. `errorHandler.js` lacked a handler for `CastError`, treating it as an internal server error (500).
- **Impact:** Pollutes server error logs and violates the REST API contract.
- **Recommended Remediation:** Add explicit `err.name === 'CastError'` branch in `errorHandler.js` returning 400 Bad Request with `INVALID_ID`.
- **Status:** **FIXED & VERIFIED**
- **Verification Evidence:** Regression test added in `backend/tests/app.test.js` (`PUT /api/logs/not-a-valid-object-id`). Test passes with HTTP 400 and `error: 'INVALID_ID'`.

#### ISS-06 (SEC-06) — Deleted User Session Causes Unhandled Null Dereference (500)
- **Category:** Session Handling / Robustness
- **Severity:** P2 (Medium)
- **Confidence:** Confirmed
- **Affected Files:** [`backend/src/controllers/authController.js`](../../backend/src/controllers/authController.js), [`backend/src/services/dashboardService.js`](../../backend/src/services/dashboardService.js), [`backend/tests/app.test.js`](../../backend/tests/app.test.js)
- **Root Cause:** If a user account was deleted from MongoDB while their browser retained an active session, `User.findById(...)` returned null. Calling `user._id` or `user.toPublic()` threw an unhandled `TypeError`.
- **Impact:** Stuck frontend state that crashes with 500 error instead of prompting the user to re-authenticate.
- **Recommended Remediation:** Add null-safety guards in `/api/auth/me` and `getDashboard`, destroying the session and returning 401 Unauthorized.
- **Status:** **FIXED & VERIFIED**
- **Verification Evidence:** Added null check and session cleanup in `authController.js`. Regression test added in `backend/tests/app.test.js` confirming 401 response. Test passes.

#### ISS-07 (ARCH-02) — Hardcoded Loopback Binding in Server Startup
- **Category:** Operations / Deployment
- **Severity:** P2 (Medium)
- **Confidence:** Confirmed
- **Affected Files:** [`backend/src/server.js`](../../backend/src/server.js), [`backend/src/config/env.js`](../../backend/src/config/env.js)
- **Root Cause:** `app.listen(env.port, '127.0.0.1')` was hardcoded to loopback.
- **Impact:** In Docker, Kubernetes, or cloud PaaS platforms, binding to `127.0.0.1` prevents incoming container traffic routing.
- **Recommended Remediation:** Make host binding configurable via `HOST` env variable (defaulting to `0.0.0.0` in production).
- **Status:** **FIXED & VERIFIED**
- **Verification Evidence:** Updated `env.js` and `server.js` to bind to `env.host`.

#### ISS-08 (ARCH-03) — Missing Graceful Process Shutdown (SIGTERM/SIGINT)
- **Category:** Operations / Reliability
- **Severity:** P2 (Medium)
- **Confidence:** Confirmed
- **Affected Files:** [`backend/src/server.js`](../../backend/src/server.js)
- **Root Cause:** No signal listeners existed on `process`.
- **Impact:** When stopped by container orchestrators, active HTTP connections and in-flight MongoDB transactions were abruptly terminated.
- **Recommended Remediation:** Add `SIGTERM` and `SIGINT` handlers that close the HTTP server and Mongoose connection cleanly.
- **Status:** **FIXED & VERIFIED**
- **Verification Evidence:** Handlers implemented in `backend/src/server.js` with timeout safety.

#### ISS-09 (ARCH-04) — Model Persistence Discrepancy on Fresh Clones
- **Category:** AI/ML / Reproducibility
- **Severity:** P2 (Medium)
- **Confidence:** Confirmed
- **Affected Files:** [`ai-ml/app/prediction/predictor.py`](../../ai-ml/app/prediction/predictor.py), [`ai-ml/app/config.py`](../../ai-ml/app/config.py)
- **Root Cause:** `config.py` specified `MODEL_PATH = ... / "model.pkl"`. However, `.gitignore` excludes `model.pkl`, whereas `random_forest_model.joblib` is version-controlled. On fresh clones, `model.pkl` is absent.
- **Impact:** Fresh repository checkouts failed to load the model in `predictor.py` unless retrained.
- **Recommended Remediation:** Add fallback detection in `predictor.py` to check for `random_forest_model.joblib`.
- **Status:** **FIXED & VERIFIED**
- **Verification Evidence:** Added fallback resolution in `predictor.py:load_model`. Pytest suite loads model successfully and passes 9/9.

#### ISS-10 (TEST-01) — Root `npm run test:ml` Ran System Python Instead of Virtualenv
- **Category:** Testing / Environment
- **Severity:** P2 (Medium)
- **Confidence:** Confirmed
- **Affected Files:** [`package.json`](../../package.json), [`scripts/test-ml.js`](../../scripts/test-ml.js)
- **Root Cause:** `package.json` ran `python -m pytest -q` which executed system Python where Starlette 0.27 conflicted with httpx 0.28.1.
- **Impact:** Root test execution failed even though the project's `.venv` contained passing dependencies.
- **Recommended Remediation:** Create a cross-platform test launcher `scripts/test-ml.js` that detects `.venv` Python executable.
- **Status:** **FIXED & VERIFIED**
- **Verification Evidence:** Created `scripts/test-ml.js` and updated `package.json`. Executed `npm run test:ml` from root: **9 passed in 2.79s**.

---

### P3 — Low / Informational Issues

#### ISS-11 (ARCH-01) — Circular Self-Reference Dependency in package.json
- **Category:** Code Quality / Dependencies
- **Severity:** P3 (Low)
- **Confidence:** Confirmed
- **Affected Files:** [`backend/package.json`](../../backend/package.json), [`frontend/package.json`](../../frontend/package.json)
- **Root Cause:** Both packages declared `"wellness-system": "file:.."` as a dependency without using it.
- **Impact:** Created circular link in npm workspace tree; risk of build issues in container packaging.
- **Recommended Remediation:** Remove `"wellness-system": "file:.."` from dependencies.
- **Status:** **FIXED & VERIFIED**
- **Verification Evidence:** Removed from both `package.json` files; confirmed clean test and build runs.

#### ISS-12 (CONF-02) — Inconsistent MongoDB URI Variable in dedupe.js
- **Category:** Configuration / Data Management
- **Severity:** P3 (Low)
- **Confidence:** Confirmed
- **Affected Files:** [`backend/src/seed/dedupe.js`](../../backend/src/seed/dedupe.js)
- **Root Cause:** `dedupe.js` checked `MONGODB_URI` instead of standard `MONGO_URI`.
- **Impact:** If `MONGO_URI` was configured in `.env`, `dedupe.js` fell back to default localhost.
- **Recommended Remediation:** Standardize on `process.env.MONGO_URI || process.env.MONGODB_URI`.
- **Status:** **FIXED & VERIFIED**
- **Verification Evidence:** Updated `dedupe.js` line 7 to check `MONGO_URI` first.

#### ISS-13 (SEC-07) — Missing Content-Security-Policy (CSP) Header
- **Category:** Security / Headers
- **Severity:** P3 (Low)
- **Confidence:** Confirmed
- **Affected Files:** [`backend/src/app.js`](../../backend/src/app.js)
- **Root Cause:** Security headers middleware set `X-Frame-Options`, `X-Content-Type-Options`, and `X-XSS-Protection`, but omitted CSP.
- **Impact:** Reduced defense-in-depth against third-party script injection.
- **Recommended Remediation:** Implement `helmet` or explicit CSP header during production proxy deployment.
- **Status:** **OPEN (Roadmap)**
- **Verification Evidence:** Tracked for deployment configuration milestone.

#### ISS-14 (TEST-02) — Open Handle from Rate Limiter Cleanup Interval
- **Category:** Code Quality / Testing
- **Severity:** P3 (Low)
- **Confidence:** Confirmed
- **Affected Files:** [`backend/src/middleware/rateLimiter.js`](../../backend/src/middleware/rateLimiter.js)
- **Root Cause:** Periodic 5-minute cleanup interval ran during Jest tests, triggering open handle warnings.
- **Impact:** Requires `--forceExit` flag in Jest test runner.
- **Recommended Remediation:** Skip starting the interval when `process.env.NODE_ENV === 'test'`.
- **Status:** **FIXED & VERIFIED**
- **Verification Evidence:** Guarded interval in `rateLimiter.js:5-14`. Verified clean Jest execution.

#### ISS-15 (DB-01) — Unbounded Foods Query
- **Category:** Performance / Scalability
- **Severity:** P3 (Low)
- **Confidence:** Confirmed
- **Affected Files:** [`backend/src/controllers/nutritionController.js`](../../backend/src/controllers/nutritionController.js)
- **Root Cause:** `Food.find(filter).sort(...)` had no limit clause.
- **Impact:** Potential memory bloat if food database grows to tens of thousands of items.
- **Recommended Remediation:** Add `.limit(Math.min(Number(req.query.limit || 200), 500))`.
- **Status:** **FIXED & VERIFIED**
- **Verification Evidence:** Added limit guard in `nutritionController.js:22`.

#### ISS-16 (OPS-03) — Lack of Containerization & CI/CD Pipelines
- **Category:** DevOps / Operations
- **Severity:** P3 (Low)
- **Confidence:** Confirmed
- **Affected Files:** Repository root
- **Root Cause:** No Dockerfile, docker-compose, or GitHub Actions workflow exists.
- **Impact:** Manual deployment steps required; tests are not automatically enforced on pull requests.
- **Recommended Remediation:** Add `.github/workflows/ci.yml` and multi-stage `Dockerfile`.
- **Status:** **OPEN (Roadmap)**
- **Verification Evidence:** Detailed implementation steps provided in `REMEDIATION_PLAN.md`.
