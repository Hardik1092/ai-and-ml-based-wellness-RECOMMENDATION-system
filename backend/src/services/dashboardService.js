const { User } = require('../models');
const { getProfileOrNone } = require('./profileService');
const { buildContext } = require('./recommendationService');
const { calculateWellnessScore, getLogs } = require('./wellnessService');
const { DISCLAIMER } = require('../utils/constants');
const { NotFoundError, ValidationError } = require('../utils/errors');
const { todayIso } = require('../utils/validators');

async function getDashboard(userId, range = 7) {
  const user = await User.findById(userId);
  if (!user) {
    throw new NotFoundError('User account not found.');
  }
  const profileDoc = await getProfileOrNone(userId);
  if (!profileDoc) {
    return {
      user: user.toPublic(false),
      profile_complete: false,
      message: 'Complete your profile to unlock your dashboard.',
      today: todayIso(),
      disclaimer: DISCLAIMER,
    };
  }
  const days = Number(range);
  if (![7, 30, 90].includes(days)) {
    throw new ValidationError('Range must be one of 7, 30 or 90.');
  }
  const ctx = await buildContext(userId, profileDoc, days);
  const score = calculateWellnessScore(await getLogs(userId, 7), ctx.metrics);
  const series = [...ctx.logs].reverse().map((l) => l.toPublic());
  return {
    user: user.toPublic(true),
    profile_complete: true,
    today: todayIso(),
    range: days,
    metrics: ctx.metrics,
    profile: profileDoc.toPublic(),
    summary: ctx.summary,
    wellness_score: score,
    top_recommendations: ctx.rules.rules.slice(0, 5),
    ml: ctx.ml,
    source: ctx.source,
    charts: {
      dates: series.map((r) => r.date),
      weight: series.map((r) => r.weight),
      water: series.map((r) => r.water),
      sleep: series.map((r) => r.sleep),
      steps: series.map((r) => r.steps),
      exercise_minutes: series.map((r) => r.exercise_minutes),
      calories: series.map((r) => r.calories),
    },
    has_logs: Boolean(series.length),
    disclaimer: DISCLAIMER,
  };
}

module.exports = { getDashboard };
