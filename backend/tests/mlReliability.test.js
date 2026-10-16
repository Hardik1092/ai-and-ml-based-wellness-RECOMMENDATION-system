const { env } = require('../src/config/env');
const { validateNumber } = require('../src/utils/validators');
const { ask } = require('../src/services/aiService');

test('ordinary users cannot start global model retraining', async () => {
  const agent = await global.authAgent('ml-admin-check@test.com');
  expect((await agent.post('/api/ml/retrain').send({})).status).toBe(403);
  const id = (await agent.get('/api/auth/me')).body.data.id;
  env.mlAdminUserIds = [id];
  try {
    expect((await agent.post('/api/ml/retrain').send({})).status).toBe(200);
  } finally { env.mlAdminUserIds = []; }
});

test.each([Infinity, -Infinity, NaN, true, [], {}])('non-finite or malformed input %p is rejected', (value) => {
  expect(() => validateNumber(value, 'calories')).toThrow();
});

test('urgent symptom message works without external provider', async () => {
  const result = await ask('I have chest pain and cannot breathe', '');
  expect(result.provider).toBe('safety_rules');
  expect(result.reply).toContain('local emergency service');
});
