# Safe Remediation Plan & Roadmap — CEP_Project

**Audit Date:** 2026-10-16  
**Auditor:** Principal Software Architect & Application Security Engineer  
**Repository:** `CEP_Project`  
**Git HEAD:** `c73d342`  

---

## 1. Remediation Strategy & Guiding Principles

1. **Safety First:** Make the smallest possible change that resolves the defect without altering application logic or API contracts.
2. **Preserve Business & Clinical Logic:** Do not modify metabolic calculations, BMR/TDEE formulas, or allergen rule sets.
3. **No External Mocking:** Maintain real database schemas, real model paths, and actual session mechanisms.
4. **Zero Regressions:** Every modified module must be re-verified against the automated test suites (`backend/` Jest and `ai-ml/` Pytest).

---

## 2. Prioritized Remediation Roadmap

### Sprint 1: P1 High Priority Fixes (Security & Resource Protection)

#### REM-01: Mount Global API Rate Limiter
- **Target Issue:** ISS-01 (SEC-01)
- **Files to Modify:** `backend/src/app.js`
- **Action:** Import `apiLimiter` from `./middleware/rateLimiter` and apply it to `/api/` before route mounts:
  ```javascript
  const { apiLimiter } = require('./middleware/rateLimiter');
  // ...
  app.use('/api', apiLimiter);
  ```
- **Acceptance Criteria:** Rapid successive requests exceeding 120 req/min receive HTTP 429 Too Many Requests. All existing 41 backend tests continue to pass.

#### REM-02: Guard Model Retraining Endpoint
- **Target Issue:** ISS-02 (SEC-02)
- **Files to Modify:** `backend/src/routes/mlRoutes.js`, `backend/src/middleware/rateLimiter.js`
- **Action:** Apply a strict rate limiter (e.g. max 2 requests per 10 minutes) on `/api/ml/retrain` to prevent CPU exhaustion.
- **Acceptance Criteria:** Repeated retraining triggers are throttled with HTTP 429.

---

### Sprint 2: P2 Medium Priority Fixes (Reliability & Robustness)

#### REM-03: Catch Mongoose CastError in Error Handler
- **Target Issue:** ISS-05 (SEC-05)
- **Files to Modify:** `backend/src/middleware/errorHandler.js`
- **Action:** Add branch for `err.name === 'CastError'`:
  ```javascript
  if (err.name === 'CastError') {
    return res.status(400).json({
      success: false,
      message: `Invalid format for identifier: ${err.path || 'id'}`,
      error: 'INVALID_ID',
    });
  }
  ```
- **Acceptance Criteria:** Requests with malformed ObjectIds receive HTTP 400 instead of HTTP 500.

#### REM-04: Prevent Null User Dereference on Stale Sessions
- **Target Issue:** ISS-06 (SEC-06)
- **Files to Modify:** `backend/src/controllers/authController.js`, `backend/src/controllers/dashboardController.js`
- **Action:** In `me` and `dashboard`, verify `user` exists. If null, destroy session and return `401 Unauthorized` with `AuthError`.
- **Acceptance Criteria:** Deleted user accounts with surviving session cookies receive HTTP 401 instead of crashing with HTTP 500.

#### REM-05: Secure Gemini API Key via Request Header
- **Target Issue:** ISS-04 (SEC-04)
- **Files to Modify:** `backend/src/services/aiService.js`
- **Action:** Remove `?key=${apiKey}` query parameter and transmit `x-goog-api-key: apiKey` in request headers.
- **Acceptance Criteria:** API key is omitted from the request URL, preventing proxy log exposure.

#### REM-06: Configurable Server Host & Graceful Process Shutdown
- **Target Issue:** ISS-07 (ARCH-02), ISS-08 (ARCH-03)
- **Files to Modify:** `backend/src/server.js`, `backend/src/config/env.js`
- **Action:**
  - Support `HOST` environment variable (default `0.0.0.0` or `127.0.0.1` based on config).
  - Add `process.on('SIGTERM', ...)` and `process.on('SIGINT', ...)` to close HTTP server and Mongoose connection cleanly.
- **Acceptance Criteria:** Server allows container ingress and exits cleanly without dropping active connections.

#### REM-07: Fallback Model Path Resolution in AI/ML Service
- **Target Issue:** ISS-09 (ARCH-04)
- **Files to Modify:** `ai-ml/app/prediction/predictor.py`
- **Action:** If `model.pkl` does not exist, check for `random_forest_model.joblib` before throwing `FileNotFoundError`.
- **Acceptance Criteria:** Service successfully loads the committed model file on fresh checkouts.

#### REM-08: Ensure Root `test:ml` Detects Virtual Environment
- **Target Issue:** ISS-10 (TEST-01)
- **Files to Modify:** `package.json`
- **Action:** Update `"test:ml"` script or provide cross-platform runner script matching `scripts/start-ml.js` logic.
- **Acceptance Criteria:** `npm run test:ml` succeeds out-of-the-box using the project's virtualenv.

---

### Sprint 3: P3 Low Priority Quality Improvements

#### REM-09: Remove Circular Workspace Dependencies
- **Target Issue:** ISS-11 (ARCH-01)
- **Files to Modify:** `backend/package.json`, `frontend/package.json`
- **Action:** Remove `"wellness-system": "file:.."` from `dependencies`.
- **Acceptance Criteria:** Clean `npm install` without cyclic dependency links.

#### REM-10: Clean Background Interval During Tests in Rate Limiter
- **Target Issue:** ISS-14 (TEST-02)
- **Files to Modify:** `backend/src/middleware/rateLimiter.js`
- **Action:** Only start the cleanup `setInterval` when `process.env.NODE_ENV !== 'test'`.
- **Acceptance Criteria:** Jest tests complete without open handle warnings.

#### REM-11: Standardize MongoDB URI in dedupe.js
- **Target Issue:** ISS-12 (CONF-02)
- **Files to Modify:** `backend/src/seed/dedupe.js`
- **Action:** Support `process.env.MONGO_URI || process.env.MONGODB_URI`.
- **Acceptance Criteria:** `dedupe.js` respects standard `MONGO_URI`.

---

### Sprint 4: Operational & Deployment Roadmap (Remaining Open Items)

#### REM-12: Configure Content-Security-Policy (CSP) Header
- **Target Issue:** ISS-13 (SEC-07)
- **Component:** `backend/src/app.js` or Production Reverse Proxy (Nginx)
- **Action:** Add `Content-Security-Policy` header allowing self-origin scripts, fonts, and styles, or integrate `helmet({ contentSecurityPolicy: ... })`.
- **Acceptance Criteria:** Responses from backend include CSP header restricting unauthorized script execution.
- **Status:** Open (Target: Staging/Production Deployment).

#### REM-13: Add Docker Containerization & CI/CD Pipelines
- **Target Issue:** ISS-16 (OPS-03)
- **Component:** Repository Root (`Dockerfile`, `docker-compose.yml`, `.github/workflows/ci.yml`)
- **Action:** 
  1. Add a multi-stage `Dockerfile` building the Vite frontend and packaging the Node.js backend.
  2. Add `docker-compose.yml` orchestrating MongoDB, Express API, and FastAPI ML service.
  3. Add GitHub Actions CI workflow executing `npm test --prefix backend`, `npm run test:ml`, and `npm run build` on all PRs.
- **Acceptance Criteria:** Single-command local startup via `docker-compose up` and automated pull request status checks.
- **Status:** Open (Target: Production Release Milestone).

---

## 3. Milestone & Release Verification Matrix

| Milestone | Scope | Criteria | Verification Document | Status |
|---|---|---|---|:---:|
| **Milestone 1: Code Remediation** | P1 & P2 Defects (ISS-01 to ISS-10) | 100% automated test pass rate | [`REMEDIATION_LOG.md`](REMEDIATION_LOG.md) | **COMPLETE** |
| **Milestone 2: Code Quality & Bounds** | P3 Code Defects (ISS-11, 12, 14, 15) | Clean packages, query limits, dedupe | [`TEST_RESULTS.md`](TEST_RESULTS.md) | **COMPLETE** |
| **Milestone 3: Release Review** | Documentation & Verification | All 12 audit docs generated | [`FINAL_AUDIT_SUMMARY.md`](FINAL_AUDIT_SUMMARY.md) | **COMPLETE** |
| **Milestone 4: Cloud Deployment** | Operations & CI/CD (ISS-13, ISS-16) | Docker containers, CI pipeline, CSP | [`PRODUCTION_READINESS.md`](PRODUCTION_READINESS.md) | Planned |
