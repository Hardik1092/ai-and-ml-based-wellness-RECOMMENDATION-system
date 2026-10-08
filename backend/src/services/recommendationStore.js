const { Recommendation } = require('../models');
const { todayIso } = require('../utils/validators');

function extractIds(result, key) {
  const plan = result.plan || {};
  const ids = [];
  if (key === 'food') {
    for (const meal of Object.values(plan.meals || {})) {
      for (const item of meal.items || []) ids.push(String(item.food_id));
    }
  } else {
    for (const item of plan.activities || []) ids.push(String(item.activity_id));
    for (const day of plan.days || []) ids.push(String(day.activity_id));
  }
  return ids.filter(Boolean);
}

async function storeRecommendation(userId, recType, result) {
  const ml = result.ml || {};
  const recDate = todayIso();
  const update = {
    foodIds: recType === 'nutrition' ? extractIds(result, 'food') : [],
    activityIds: recType === 'activity' ? extractIds(result, 'activity') : [],
    summary: (result.why || '').slice(0, 2000),
    mlPrediction: ml.category || null,
    mlConfidence: ml.confidence ?? null,
    source: result.source || 'hybrid',
    payload: { targets: (result.plan || {}).targets, metrics: result.metrics },
  };

  const record = await Recommendation.findOneAndUpdate(
    { userId, recDate, recType },
    { $set: update },
    { new: true, upsert: true }
  );
  return record;
}

module.exports = { storeRecommendation };
