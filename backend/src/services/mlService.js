const { env } = require('../config/env');

let overridePredict = null;

function setPredictOverride(fn) {
  overridePredict = fn;
}

function unavailable(reason) {
  return { available: false, reason };
}

function mapPrediction(payload) {
  if (!payload || payload.available === false) {
    return unavailable(payload?.reason || 'ML service returned unavailable.');
  }
  const category = payload.category;
  return {
    available: true,
    category,
    category_label: payload.categoryLabel || payload.category_label || (category || '').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
    categoryLabel: payload.categoryLabel || payload.category_label,
    confidence: payload.confidence,
    probabilities: payload.probabilities || {},
    top_features: payload.topFeatures || payload.top_features || [],
    topFeatures: payload.topFeatures || payload.top_features || [],
    explanation: payload.explanation,
    model_type: payload.modelType || payload.model_type || 'RandomForestClassifier',
    modelType: payload.modelType || payload.model_type,
  };
}

async function fetchJson(path, { method = 'GET', body, timeoutMs } = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs || env.mlTimeoutMs);
  try {
    const res = await fetch(`${env.mlServiceUrl}${path}`, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
    const data = await res.json().catch(() => null);
    return { ok: res.ok, status: res.status, data };
  } finally {
    clearTimeout(timer);
  }
}

async function predictCategory(features, { enabled = env.mlEnabled } = {}) {
  if (overridePredict) return overridePredict(features);
  if (!enabled) {
    return unavailable('ML is disabled by configuration (ML_ENABLED=false).');
  }
  try {
    const { ok, data } = await fetchJson('/predict', { method: 'POST', body: { features } });
    if (!ok || !data) return unavailable('Model file could not be loaded; using rule-based output.');
    return mapPrediction(data);
  } catch (err) {
    return unavailable('Prediction failed; using rule-based output.');
  }
}

async function getModelMetadata() {
  try {
    const { ok, data } = await fetchJson('/model/metadata');
    if (!ok || !data) return null;
    return data;
  } catch {
    return null;
  }
}

async function getModelExplanation() {
  try {
    const { ok, data } = await fetchJson('/model/explanation');
    if (!ok || !data) return null;
    return data;
  } catch {
    return null;
  }
}

async function retrain(extraRows = [], extraLabels = [], { force = false } = {}) {
  try {
    const { ok, data } = await fetchJson('/retrain', {
      method: 'POST',
      body: { extra_rows: extraRows, extra_labels: extraLabels, force },
      timeoutMs: 120000,
    });
    if (!ok || !data) return { available: false, reason: 'Retrain request failed.' };
    return data;
  } catch {
    return { available: false, reason: 'Retrain request failed.' };
  }
}

module.exports = {
  setPredictOverride,
  predictCategory,
  getModelMetadata,
  getModelExplanation,
  retrain,
};
