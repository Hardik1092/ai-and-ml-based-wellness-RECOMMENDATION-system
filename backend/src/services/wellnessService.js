const { UserLog } = require('../models');
const {
  EXERCISE_MINUTES_TARGET, SLEEP_TARGET_HOURS, STEPS_TARGET, WELLNESS_SCORE_WEIGHTS,
} = require('../utils/constants');

function daysAgoIso(days) {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() - (days - 1));
  return d.toISOString().slice(0, 10);
}

async function getLogs(userId, days = 7) {
  const since = daysAgoIso(days);
  return UserLog.find({ userId, logDate: { $gte: since } }).sort({ logDate: -1 });
}

function avg(values) {
  const nums = values.filter((v) => v !== null && v !== undefined);
  if (!nums.length) return null;
  return nums.reduce((a, b) => a + b, 0) / nums.length;
}

function summariseLogs(logs) {
  return {
    count: logs.length,
    avg_sleep: avg(logs.map((l) => l.sleep)),
    avg_water: avg(logs.map((l) => l.water)),
    avg_steps: avg(logs.map((l) => l.steps)),
    avg_exercise_minutes: avg(logs.map((l) => l.exerciseMinutes)),
    avg_calories: avg(logs.map((l) => l.calories)),
    avg_mood: avg(logs.map((l) => l.mood)),
    avg_stress: avg(logs.map((l) => l.stress)),
    latest_weight: (logs.find((l) => l.weight !== null && l.weight !== undefined) || {}).weight ?? null,
  };
}

function ratioScore(actual, target, overPenalty = false) {
  if (actual === null || actual === undefined || !target) return null;
  let ratio = actual / target;
  if (overPenalty && ratio > 1.15) ratio = Math.max(0, 2 - ratio);
  return Math.round(Math.min(ratio, 1) * 100);
}

function calculateWellnessScore(logs, metrics) {
  const summary = summariseLogs(logs);
  if (!logs.length) {
    return {
      available: false,
      label: 'Weekly Wellness Engagement Score',
      message: 'No data yet. Log a few days of wellness data to see your score.',
      categories: {},
      overall: null,
    };
  }

  const catEntries = [];

  const rawNutrition = ratioScore(summary.avg_calories, metrics.calorie_target, true);
  if (rawNutrition !== null) {
    catEntries.push({ key: 'nutrition', score: rawNutrition, note: 'How close your logged intake was to your calorie target.' });
  } else {
    catEntries.push({ key: 'nutrition', score: null, note: 'No calorie intake logged yet this week.' });
  }

  const hasActivity = summary.avg_steps !== null || summary.avg_exercise_minutes !== null;
  if (hasActivity) {
    const sScore = ratioScore(summary.avg_steps, STEPS_TARGET) ?? 50;
    const mScore = ratioScore(summary.avg_exercise_minutes, EXERCISE_MINUTES_TARGET) ?? 50;
    const actScore = Math.round(0.5 * sScore + 0.5 * mScore);
    catEntries.push({ key: 'activity', score: actScore, note: 'Average of your step and exercise-minute achievement.' });
  } else {
    catEntries.push({ key: 'activity', score: null, note: 'No movement or steps recorded yet this week.' });
  }

  const rawSleep = ratioScore(summary.avg_sleep, SLEEP_TARGET_HOURS);
  if (rawSleep !== null) {
    catEntries.push({ key: 'sleep', score: rawSleep, note: `Logged sleep against the ${SLEEP_TARGET_HOURS} h guideline.` });
  } else {
    catEntries.push({ key: 'sleep', score: null, note: 'No sleep duration logged yet this week.' });
  }

  const rawHydration = ratioScore(summary.avg_water, metrics.water_target_ml);
  if (rawHydration !== null) {
    catEntries.push({ key: 'hydration', score: rawHydration, note: 'Logged water against your personal water target.' });
  } else {
    catEntries.push({ key: 'hydration', score: null, note: 'No water intake logged yet this week.' });
  }

  const scoredEntries = catEntries.filter((c) => c.score !== null);
  const overall = scoredEntries.length
    ? Math.round(scoredEntries.reduce((s, c) => s + c.score, 0) / scoredEntries.length)
    : Math.round(Math.min(summary.count / 7, 1) * 75);

  const categories = Object.fromEntries(
    catEntries.map((c) => [
      c.key,
      {
        score: c.score,
        weight: WELLNESS_SCORE_WEIGHTS[c.key],
        note: c.note,
      },
    ]),
  );

  return {
    available: true,
    label: 'Weekly Wellness Engagement Score',
    disclaimer: 'This is an engagement metric for this project, not a medical score.',
    categories,
    overall,
    days_logged: summary.count,
  };
}

module.exports = { getLogs, summariseLogs, calculateWellnessScore };
