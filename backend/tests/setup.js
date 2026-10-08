process.env.MONGOMS_MD5_CHECK = '0';
const { MongoMemoryServer } = require('mongodb-memory-server');
const mongoose = require('mongoose');
const request = require('supertest');
const { createApp } = require('../src/app');
const { seedActivities, seedFoods } = require('../src/seed/seed');
const { env } = require('../src/config/env');
const { setPredictOverride } = require('../src/services/mlService');

global.VALID_PROFILE = {
  age: 24, gender: 'male', height_cm: 175, weight_kg: 78,
  activity_level: 'light', food_preference: 'vegetarian',
  allergies: ['peanut'], sleep_hours: 6.5, goal: 'weight_loss',
};

const HYBRID_ML = {
  available: true,
  category: 'fitness_improvement',
  category_label: 'Fitness Improvement',
  confidence: 0.84,
  probabilities: { fitness_improvement: 0.84, balanced_wellness: 0.16 },
  top_features: [{ feature: 'bmi', importance: 0.21 }],
  explanation: 'The model predicted fitness improvement.',
  model_type: 'RandomForestClassifier',
};

let mongo;

beforeAll(async () => {
  mongo = await MongoMemoryServer.create();
  await mongoose.connect(mongo.getUri());
  await seedFoods();
  await seedActivities();
  global.__APP__ = createApp();
}, 120000);

afterAll(async () => {
  await mongoose.disconnect();
  if (mongo) await mongo.stop();
});

beforeEach(() => {
  env.mlEnabled = true;
  setPredictOverride(() => ({ ...HYBRID_ML }));
});

global.register = async function register(agent, email = 'user@test.com', password = 'Passw0rd1', name = 'Test User') {
  return agent.post('/api/auth/register').send({ name, email, password });
};

global.authAgent = async function authAgent(email = 'user@test.com') {
  const agent = request.agent(global.__APP__);
  await global.register(agent, email);
  await agent.put('/api/profile').send(global.VALID_PROFILE);
  return agent;
};

global.getApp = () => global.__APP__;
