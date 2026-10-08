const { MLTrainingRun } = require('../models');
const { FEATURE_DESCRIPTIONS } = require('../utils/constants');
const { getModelExplanation, getModelMetadata } = require('../services/mlService');
const { getProfile } = require('../services/profileService');
const { buildContext } = require('../services/recommendationService');
const { buildTrainingRowsFromFeedback } = require('../services/feedbackService');
const { retrain } = require('../services/mlService');
const { env } = require('../config/env');
const { success } = require('../utils/responses');
const { currentUserId } = require('../utils/security');
const { asyncHandler } = require('../middleware/validation');

const explanation = asyncHandler(async (req, res) => {
  const userId = currentUserId(req);
  const profile = await getProfile(userId);
  const ctx = await buildContext(userId, profile);
  const metadata = await getModelMetadata();
  const extra = await getModelExplanation();

  const rawMeta = extra || metadata;
  const serviceOnline = Boolean(rawMeta && (rawMeta.available !== false || rawMeta.model_type));
  const merged = { ...(extra || {}), ...(metadata || {}) };
  const modelLoaded = Boolean(serviceOnline && merged.model_type && merged.metrics);
  const modelAvailable = Boolean(modelLoaded && ctx.ml?.available);

  const importances = merged.feature_importances || merged.featureImportances || {};
  const ranked = Object.entries(importances).sort((a, b) => b[1] - a[1]);
  const runs = await MLTrainingRun.find().sort({ createdAt: -1 }).limit(5);

  const nSamples = modelLoaded ? (merged.n_samples ?? merged.nSamples ?? null) : null;
  const modelType = modelLoaded ? (merged.model_type || merged.modelType || null) : null;
  const metrics = modelLoaded && merged.metrics ? {
    accuracy: typeof merged.metrics.accuracy === 'number' ? merged.metrics.accuracy : null,
    precision: typeof merged.metrics.precision === 'number' ? merged.metrics.precision : null,
    recall: typeof merged.metrics.recall === 'number' ? merged.metrics.recall : null,
    f1: typeof merged.metrics.f1 === 'number' ? merged.metrics.f1 : null,
  } : null;

  return success(res, {
    service_online: serviceOnline,
    model_loaded: modelLoaded,
    model_available: modelAvailable,
    ml_enabled: env.mlEnabled,
    status_label: modelAvailable ? 'ready' : (serviceOnline ? 'online_fallback' : 'offline'),
    fallback_active: !modelAvailable,
    fallback_reason: !serviceOnline
      ? 'Machine learning service (port 8000) is currently offline. Recommendations are running on deterministic clinical safety rules.'
      : (!ctx.ml?.available ? (ctx.ml?.reason || 'Recommendation engine is operating in deterministic safety mode.') : null),
    model_type: modelType,
    model_architecture: modelType,
    modelArchitecture: modelType,
    model_params: modelLoaded ? (merged.model_params || merged.modelParams || {}) : null,
    trained_at: modelLoaded ? (merged.trained_at || merged.trainedAt || null) : null,
    data_source: modelLoaded ? (merged.data_source || merged.dataSource || null) : null,
    n_samples: nSamples,
    nSamples: nSamples,
    training_samples: nSamples,
    trainingSamples: nSamples,
    metrics,
    confusion_matrix: modelLoaded ? (merged.confusion_matrix || merged.confusionMatrix || null) : null,
    confusion_labels: modelLoaded ? (merged.confusion_labels || merged.confusionLabels || []) : [],
    classes: modelLoaded ? (merged.classes || []) : [],
    feature_importances: ranked.map(([name, value]) => ({
      feature: name,
      importance: value,
      description: FEATURE_DESCRIPTIONS[name] || '',
    })),
    featureImportances: ranked.map(([name, value]) => ({
      feature: name,
      importance: value,
      description: FEATURE_DESCRIPTIONS[name] || '',
    })),
    your_features: ctx.features,
    feature_descriptions: FEATURE_DESCRIPTIONS,
    prediction: ctx.ml,
    training_runs: runs.map((r) => r.toPublic()),
  });
});

const retrainFromFeedback = asyncHandler(async (_req, res) => {
  const { rows, labels } = await buildTrainingRowsFromFeedback();
  if (!rows || rows.length < 5) {
    return success(res, {
      retrained: false,
      n_samples: rows ? rows.length : 0,
      reason: 'Insufficient feedback data for retraining. At least 5 positively-rated plans are required to fine-tune the model.',
    }, 'Insufficient feedback data for retraining.');
  }

  const result = await retrain(rows, labels, { force: false });
  if (result && result.metrics) {
    await MLTrainingRun.create({
      modelType: result.model_type || result.modelType || 'RandomForestClassifier',
      nSamples: result.n_samples || result.nSamples || rows.length,
      accuracy: result.metrics.accuracy,
      precision: result.metrics.precision,
      recall: result.metrics.recall,
      f1: result.metrics.f1,
      promoted: Boolean(result.promoted),
      notes: `${rows.length} feedback-derived rows included`,
    });
  }
  return success(res, result, result.promoted ? 'Model retrained and promoted.' : 'Retraining completed.');
});

module.exports = { explanation, retrainFromFeedback };
