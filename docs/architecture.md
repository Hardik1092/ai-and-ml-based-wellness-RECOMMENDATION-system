# Architecture

MERN application plus a separate Python ML service.

```
React (Vite, JSX)
        |
        | REST / JSON, HTTP-only session cookie
        v
Express (Node.js)
  - auth, profile, logs, dashboard, feedback
  - health metrics (BMI, BMR, TDEE, macros, water)
  - rule engine (safety first)
  - content-based scoring
  - optional AI narrative recommendations and wording
        |
        +---- MongoDB (Mongoose)
        |
        | HTTP /predict  (timeout, never fatal)
        v
FastAPI (ai-ml/)
  RandomForestClassifier + evaluation + retrain
```

## Hybrid recommendation precedence

1. User safety / allergies / diet / dislikes (hard)
2. Activity difficulty ceiling
3. Health-metric rules
4. ML focus category (bounded bonus, default cap 0.15)
5. Content-based ranking
6. Optional AI narrative recommendations and wording. The actual service can return
   generated nutrition/activity/wellness items after output filtering; this is not
   merely rewording. These filters do not establish clinical safety. See the
   [ML experiment log](CEP_ML_EXPERIMENT_LOG.md) for verified limits.

If FastAPI is down, `ML_ENABLED=false`, the model file is missing, or prediction
fails, Express continues with rules + content scoring (`source: rules_only`).

## Why the split?

Application APIs stay in JavaScript/Express so the viva story is a standard
MERN app. Training and sklearn stay in Python because that is the natural
ecosystem for the Random Forest, feature importances and confusion matrix.
