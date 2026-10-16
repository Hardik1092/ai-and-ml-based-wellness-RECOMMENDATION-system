const request = require('supertest');
const authAgent = (email) => global.authAgent(email);
const getApp = () => global.getApp();
const register = (...args) => global.register(...args);
const VALID_PROFILE = global.VALID_PROFILE;
const { UserLog } = require('../src/models');

describe('profile logs dashboard feedback isolation', () => {
  test('profile bounds', async () => {
    const agent = request.agent(getApp());
    await register(agent, 'p1@test.com');
    const res = await agent.put('/api/profile').send({ ...VALID_PROFILE, age: 3 });
    expect(res.status).toBe(422);
  });

  test('profile required for recs', async () => {
    const agent = request.agent(getApp());
    await register(agent, 'p2@test.com');
    expect((await agent.get('/api/recommendations/nutrition')).status).toBe(404);
  });

  test('logs upsert and dashboard charts', async () => {
    const agent = await authAgent('log1@test.com');
    const create = await agent.post('/api/logs').send({
      date: new Date().toISOString().slice(0, 10),
      water: 2000, sleep: 7, steps: 8000, exercise_minutes: 30, calories: 2000, mood: 4, stress: 2,
    });
    expect([200, 201]).toContain(create.status);
    const dash = await agent.get('/api/dashboard?range=7');
    expect(dash.status).toBe(200);
    expect(dash.body.data.charts.dates.length).toBeGreaterThan(0);
    const score = await agent.get('/api/wellness-score');
    expect(score.body.data.overall).toBeGreaterThanOrEqual(0);
    expect(score.body.data.overall).toBeLessThanOrEqual(100);
  });

  test('feedback and ownership', async () => {
    const a = await authAgent('own1@test.com');
    const b = await authAgent('own2@test.com');
    const rec = await a.get('/api/recommendations/nutrition');
    const id = rec.body.data.recommendation_id;
    const steal = await b.post('/api/feedback').send({ rating: 5, recommendation_id: id });
    expect(steal.status).toBe(403);
    const ok = await a.post('/api/feedback').send({
      rating: 5, followed_plan: true, recommendation_id: id, comment: 'good',
    });
    expect(ok.status).toBe(201);
    const logsA = await UserLog.find({ userId: (await a.get('/api/auth/me')).body.data.id });
    const otherLogs = await b.get('/api/logs?range=7');
    expect(otherLogs.body.data.logs.every((l) => logsA.every((x) => String(x._id) !== l.log_id))).toBe(true);
  });

  test('range validation', async () => {
    const agent = await authAgent('rng@test.com');
    expect((await agent.get('/api/dashboard?range=12')).status).toBe(422);
  });

  test('handles malformed ObjectId with 400 Bad Request', async () => {
    const agent = await authAgent('malformed@test.com');
    const res = await agent.put('/api/logs/not-a-valid-object-id').send({ water: 500 });
    expect(res.status).toBe(400);
    expect(res.body.error).toBe('INVALID_ID');
  });

  test('clears session and returns 401 if user is deleted from database', async () => {
    const agent = await authAgent('deleted@test.com');
    const meBefore = await agent.get('/api/auth/me');
    expect(meBefore.status).toBe(200);
    const userId = meBefore.body.data.id;
    const { User } = require('../src/models');
    await User.findByIdAndDelete(userId);
    const meAfter = await agent.get('/api/auth/me');
    expect(meAfter.status).toBe(401);
  });
});
