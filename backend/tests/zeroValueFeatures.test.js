const { buildFeatureRow, imputeRaw, buildMlFeatures } = require('../src/services/featureBuilder');
const { summariseLogs } = require('../src/services/wellnessService');
const { setPredictOverride } = require('../src/services/mlService');

const profile = { age: 30, gender: 'male', activity_level: 'moderate', goal: 'general_wellness', sleep_hours: 8, water_intake_ml: 2800 };
const metrics = { bmi: 22, water_target_ml: 3000, calorie_target: 2400 };

test.each(['sleep_hours', 'water_ml', 'calories'])('observed zero %s survives raw construction and imputation', (key) => {
  const raw = { bmi: 22, age: 30, sleep_hours: 8, water_ml: 3000, calories: 2400, water_target_ml: 3000, calorie_target: 2400, [key]: 0 };
  const expected = { sleep_hours: ['sleep_hours', 'sleep_adequacy'], water_ml: ['hydration_ratio', 'hydration_adequacy'], calories: ['calorie_ratio'] }[key];
  for (const input of [raw, imputeRaw(raw)]) {
    const features = buildFeatureRow(input);
    for (const feature of expected) expect(features[feature]).toBe(0);
  }
});

test.each([null, undefined])('missing log values (%p) use profile then imputation defaults', (missing) => {
  const summary = { avg_sleep: missing, avg_water: missing, avg_calories: missing };
  expect(buildMlFeatures(profile, metrics, summary)).toMatchObject({ sleep_hours: 8, hydration_ratio: 0.933, calorie_ratio: 1 });
  expect(buildMlFeatures({ ...profile, sleep_hours: missing, water_intake_ml: missing }, metrics, summary)).toMatchObject({ sleep_hours: 7, hydration_ratio: 1, calorie_ratio: 1 });
  expect(buildFeatureRow(imputeRaw({ bmi: 22, age: 30, sleep_hours: missing, water_ml: missing, calories: missing }))).toMatchObject({ sleep_hours: 7, hydration_ratio: 1, calorie_ratio: 1 });
});

test('zero logs override positive profile values; zero profile values survive absent logs', () => {
  expect(buildMlFeatures(profile, metrics, { avg_sleep: 0, avg_water: 0, avg_calories: 0 })).toMatchObject({ sleep_hours: 0, sleep_adequacy: 0, hydration_ratio: 0, hydration_adequacy: 0, calorie_ratio: 0 });
  expect(buildMlFeatures({ ...profile, sleep_hours: 0, water_intake_ml: 0 }, metrics, {})).toMatchObject({ sleep_hours: 0, hydration_ratio: 0, calorie_ratio: 1 });
});

test('log aggregation includes zeros and excludes missing observations', () => {
  const summary = summariseLogs([{ sleep: 0, water: 0, calories: 0 }, { sleep: 8, water: 3000, calories: 2400 }, { sleep: null, water: null, calories: null }]);
  expect(buildMlFeatures(profile, metrics, summary)).toMatchObject({ sleep_hours: 4, hydration_ratio: 0.5, calorie_ratio: 0.5 });
});

test('persisted zero logs reach the recommendation model request unchanged', async () => {
  const agent = await global.authAgent('zero-feature-check@example.test');
  const response = await agent.post('/api/logs').send({ date: new Date().toISOString().slice(0, 10), sleep: 0, water: 0, calories: 0 });
  expect([200, 201]).toContain(response.status);
  expect(response.body.data).toMatchObject({ sleep: 0, water: 0, calories: 0 });
  let received;
  setPredictOverride((features) => { received = features; return { available: false, reason: 'Capture-only test' }; });
  try {
    expect((await agent.get('/api/recommendations/nutrition')).status).toBe(200);
    expect(received).toMatchObject({ sleep_hours: 0, sleep_adequacy: 0, hydration_ratio: 0, hydration_adequacy: 0, calorie_ratio: 0 });
  } finally { setPredictOverride(null); }
});
