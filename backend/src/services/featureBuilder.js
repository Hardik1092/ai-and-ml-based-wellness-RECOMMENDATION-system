const { ACTIVITY_SCORES, FEATURE_NAMES, FEATURE_DESCRIPTIONS, GOALS, GENDERS, SLEEP_TARGET_HOURS, STEPS_TARGET, EXERCISE_MINUTES_TARGET } = require('../utils/constants');

const GOAL_CODES = Object.fromEntries(GOALS.map((g, i) => [g, i]));
const GENDER_CODES = Object.fromEntries(GENDERS.map((g, i) => [g, i]));

// Match Python round(float, digits): round the actual IEEE-754 value to nearest,
// ties to even. Math.round differs at boundaries such as steps / 8000 = 1.0625.
function pythonRound(value, digits) {
  value = Number(value);
  if (!Number.isFinite(value) || value === 0) return value;
  const view = new DataView(new ArrayBuffer(8));
  view.setFloat64(0, Math.abs(value));
  const bits = view.getBigUint64(0);
  const exponent = Number((bits >> 52n) & 0x7ffn);
  const fraction = bits & ((1n << 52n) - 1n);
  const mantissa = exponent === 0 ? fraction : fraction + (1n << 52n);
  const shift = (exponent === 0 ? -1022 : exponent - 1023) - 52;
  let numerator = mantissa * (10n ** BigInt(digits));
  let denominator = 1n;
  if (shift >= 0) numerator <<= BigInt(shift);
  else denominator <<= BigInt(-shift);
  let quotient = numerator / denominator;
  const twiceRemainder = (numerator % denominator) * 2n;
  if (twiceRemainder > denominator || (twiceRemainder === denominator && quotient % 2n === 1n)) quotient += 1n;
  return Math.sign(value) * Number(quotient) / (10 ** digits);
}

const IMPUTATION_DEFAULTS = {
  sleep_hours: SLEEP_TARGET_HOURS,
  water_ml: null,
  exercise_minutes: 0,
  steps: 0,
  calories: null,
  stress_level: 3,
};

function imputeRaw(raw) {
  const filled = { ...raw };
  for (const [key, def] of Object.entries(IMPUTATION_DEFAULTS)) {
    if (filled[key] === null || filled[key] === undefined) filled[key] = def;
  }
  if (filled.water_ml === null || filled.water_ml === undefined) {
    filled.water_ml = filled.water_target_ml || 2500;
  }
  if (filled.calories === null || filled.calories === undefined) {
    filled.calories = filled.calorie_target || 2000;
  }
  return filled;
}

function buildFeatureRow(raw) {
  const waterTarget = raw.water_target_ml || 2500;
  const calorieTarget = raw.calorie_target || 2000;
  const sleepHours = raw.sleep_hours ?? SLEEP_TARGET_HOURS;
  const hydrationRatio = (raw.water_ml || 0) / waterTarget;
  const exerciseMinutes = raw.exercise_minutes || 0;
  const stepsRatio = (raw.steps || 0) / STEPS_TARGET;
  const calorieRatio = (raw.calories ?? calorieTarget) / calorieTarget;

  return {
    bmi: pythonRound(raw.bmi, 2),
    age: parseInt(raw.age, 10),
    activity_score: ACTIVITY_SCORES[raw.activity_level] || 2,
    sleep_hours: pythonRound(sleepHours, 2),
    sleep_adequacy: sleepHours >= SLEEP_TARGET_HOURS ? 1 : 0,
    hydration_ratio: pythonRound(hydrationRatio, 3),
    hydration_adequacy: hydrationRatio >= 0.9 ? 1 : 0,
    exercise_minutes: pythonRound(exerciseMinutes, 1),
    exercise_adequacy: exerciseMinutes >= EXERCISE_MINUTES_TARGET ? 1 : 0,
    steps_ratio: pythonRound(stepsRatio, 3),
    calorie_ratio: pythonRound(calorieRatio, 3),
    stress_level: parseInt(raw.stress_level || 3, 10),
    goal_code: GOAL_CODES[raw.goal] ?? GOAL_CODES.general_wellness,
    gender_code: GENDER_CODES[raw.gender] ?? GENDER_CODES.other,
  };
}

function buildMlFeatures(profile, metrics, summary) {
  const raw = {
    bmi: metrics.bmi,
    age: profile.age,
    gender: profile.gender,
    weight_kg: profile.weight_kg,
    activity_level: profile.activity_level,
    goal: profile.goal,
    sleep_hours: summary.avg_sleep ?? profile.sleep_hours,
    water_ml: summary.avg_water ?? profile.water_intake_ml,
    water_target_ml: metrics.water_target_ml,
    exercise_minutes: summary.avg_exercise_minutes,
    steps: summary.avg_steps,
    calories: summary.avg_calories,
    calorie_target: metrics.calorie_target,
    stress_level: profile.stress_level || summary.avg_stress,
  };
  return buildFeatureRow(imputeRaw(raw));
}

module.exports = {
  FEATURE_NAMES,
  FEATURE_DESCRIPTIONS,
  imputeRaw,
  buildFeatureRow,
  buildMlFeatures,
};
