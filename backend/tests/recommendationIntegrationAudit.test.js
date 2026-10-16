// Audit characterization tests: defect tests assert observed behavior, not safety.
const fs = require('fs');
const path = require('path');
const { env } = require('../src/config/env');
const { setPredictOverride, predictCategory } = require('../src/services/mlService');
const { buildRecommendationPrompt } = require('../src/services/aiService');
const meta = JSON.parse(fs.readFileSync(path.join(__dirname, '../../ai-ml/models/cep-20k-v1/feature_metadata.json'), 'utf8'));
const prediction = (category) => ({ available: true, category, confidence: 0.91, probabilities: { [category]: 0.91, balanced_wellness: 0.09 }, model_type: 'HistGradientBoostingClassifier' });
const response = (body, status = 200) => ({ ok: status < 400, status, json: async () => body });
let saved, spy, requests;
beforeEach(() => {
  saved = { ...env }; requests = [];
  setPredictOverride(null);
  spy = jest.spyOn(global, 'fetch').mockImplementation(async (url, options) => {
    requests.push({ url, body: options.body ? JSON.parse(options.body) : null });
    if (url.endsWith('/predict')) return response(prediction('sleep_focus'));
    if (url.endsWith('/model/metadata') || url.endsWith('/model/explanation')) return response({ ...meta, available: true });
    throw new Error('Unexpected external request intercepted by audit');
  });
});
afterEach(() => { spy.mockRestore(); Object.assign(env, saved); setPredictOverride(null); });
const agentFor = (id) => global.authAgent(`integration-audit-${id}@example.test`);
const names = (data) => Object.values(data.plan.meals).flatMap(m => m.items.map(i => i.food_name));

test('request features, displayed features and returned probabilities share one inference', async () => {
  const agent = await agentFor('features');
  await agent.post('/api/logs').send({ date: new Date().toISOString().slice(0, 10), sleep: 0, water: 0, calories: 0, steps: 8500, exercise_minutes: 0 });
  const res = await agent.get('/api/ml/explanation');
  expect(res.status).toBe(200);
  const sent = requests.filter(r => r.url.endsWith('/predict'));
  expect(sent).toHaveLength(1);
  expect(res.body.data.your_features).toEqual(sent[0].body.features);
  expect(sent[0].body.features).toMatchObject({ sleep_hours: 0, hydration_ratio: 0, calorie_ratio: 0, steps_ratio: 1.062 });
  expect(res.body.data.prediction.probabilities).toEqual(prediction('sleep_focus').probabilities);
  expect(res.body.data.model_type).toBe('HistGradientBoostingClassifier');
});

test('changing only the ML response changes nutrition, daily activity and weekly selection', async () => {
  const agent = await agentFor('influence');
  await agent.put('/api/profile').send({ ...global.VALID_PROFILE, goal: 'general_wellness', activity_level: 'moderate' });
  const byCategory = {};
  for (const category of ['hydration_focus', 'activity_focus']) {
    spy.mockImplementation(async (url, options) => { requests.push({ url, body: JSON.parse(options.body) }); return response(prediction(category)); });
    byCategory[category] = {};
    for (const [key, route] of [['nutrition','nutrition'], ['activity','activity'], ['weekly','activity/weekly']]) {
      const res = await agent.get(`/api/recommendations/${route}`);expect(res.status).toBe(200);
      const data = res.body.data;expect(data.source).toBe('hybrid');expect(data.plan.ml_category_applied).toBe(category);
      expect(data.ml.probabilities).toEqual(prediction(category).probabilities);byCategory[category][key] = data;
    }
  }
  expect(requests.every(r => JSON.stringify(r.body.features) === JSON.stringify(requests[0].body.features))).toBe(true);
  expect(names(byCategory.hydration_focus.nutrition)).not.toEqual(names(byCategory.activity_focus.nutrition));
  expect(byCategory.hydration_focus.activity.plan.activities.map(a=>a.activity_name)).not.toEqual(byCategory.activity_focus.activity.plan.activities.map(a=>a.activity_name));
  expect(byCategory.hydration_focus.weekly.plan.days.map(d=>d.activity)).not.toEqual(byCategory.activity_focus.weekly.plan.days.map(d=>d.activity));
});

test('Gemini 404 preserves ML category and hybrid plans for every fallback route', async () => {
  env.aiProvider = 'gemini';env.geminiApiKey = 'synthetic-test-key';
  const base = spy.getMockImplementation();
  spy.mockImplementation(async (url, options) => url.includes('generativelanguage.googleapis.com') ? response({ error: { message: 'Synthetic 404: model unavailable' } },404) : base(url,options));
  const agent = await agentFor('gemini-failure');
  for (const route of ['nutrition','activity','activity/weekly','wellness']) {
    const r=await agent.get(`/api/recommendations/${route}`);expect(r.status).toBe(200);
    expect(r.body.data.source).toBe('hybrid');expect(r.body.data.ml.category).toBe('sleep_focus');
    expect(r.body.data.ml.probabilities).toEqual(prediction('sleep_focus').probabilities);
    if(r.body.data.plan)expect(r.body.data.plan.ml_category_applied).toBe('sleep_focus');
    expect(r.body.data.why).toContain('sleep focus');
  }
});

test('Gemini success retains catalog plans; generation prompt is independent of ML category', async () => {
  env.aiProvider='gemini';env.geminiApiKey='synthetic-test-key';
  const base=spy.getMockImplementation(), prompts=[];
  const narrative={summary:'Synthetic narrative.',nutrition:[{title:'Regular meals',description:'Plan meals.',priority:'medium'}],activity:[{title:'Walk',description:'Take a short walk.'}],wellness:[{title:'Routine',description:'Keep a routine.'}]};
  spy.mockImplementation(async (url,options)=>{
    if(!url.includes('generativelanguage.googleapis.com'))return base(url,options);
    prompts.push(JSON.parse(options.body).contents[0].parts[0].text);
    return response({candidates:[{content:{parts:[{text:JSON.stringify(narrative)}]}}]});
  });
  const agent=await agentFor('success');
  for(const category of ['sleep_focus','hydration_focus']){
    setPredictOverride(()=>prediction(category));
    for(const route of ['nutrition','activity','activity/weekly','wellness']) {
      const r=await agent.get(`/api/recommendations/${route}`);expect(r.status).toBe(200);
      expect(r.body.data.source).toBe('llm');expect(r.body.data.ml.category).toBe(category);
      if(r.body.data.plan)expect(r.body.data.plan.ml_category_applied).toBe(category);
      else expect(r.body.data.tips[0].message).toBe('Keep a routine.');
    }
  }
  expect(prompts).toHaveLength(8);expect(prompts.every(p=>p===prompts[0])).toBe(true);
});

test('wellness tips and dashboard top recommendations do not depend on ML category',async()=>{
  const agent=await agentFor('rules');const rows=[];
  for(const category of ['sleep_focus','hydration_focus']){
    setPredictOverride(()=>prediction(category));
    const w=await agent.get('/api/recommendations/wellness'), d=await agent.get('/api/dashboard');
    expect(w.status).toBe(200);expect(d.status).toBe(200);
    rows.push({tips:w.body.data.tips,top:d.body.data.top_recommendations});
  }
  expect(rows[0]).toEqual(rows[1]);
});

test.each(['unavailable','non-json','timeout'])('ML %s uses the rules-only fallback',async(mode)=>{
  env.mlTimeoutMs=10;
  spy.mockImplementation((_url,options)=>{
    if(mode==='timeout')return new Promise((_resolve,reject)=>options.signal.addEventListener('abort',()=>reject(new Error('Synthetic timeout'))));
    if(mode==='non-json')return Promise.resolve({ok:true,status:200,json:async()=>{throw new Error('Invalid JSON');}});
    return Promise.resolve(response({available:false,reason:'Synthetic unavailable'}));
  });
  const agent=await agentFor(mode);const r=await agent.get('/api/recommendations/nutrition');
  expect(r.status).toBe(200);expect(r.body.data.source).toBe('rules_only');expect(r.body.data.ml.available).toBe(false);expect(r.body.data.plan.ml_category_applied).toBeNull();
});

test('AUDIT DEFECT: empty JSON ML success is accepted and then causes a 500 recommendation response',async()=>{
  spy.mockResolvedValue(response({}));
  expect((await predictCategory({})).available).toBe(true);
  const agent=await agentFor('empty');expect((await agent.get('/api/recommendations/nutrition')).status).toBe(500);
});

test('AUDIT DEFECT: unknown category and invalid probabilities are trusted',async()=>{
  spy.mockResolvedValue(response({available:true,category:'unknown_category',confidence:4,probabilities:{unknown_category:-2}}));
  const agent=await agentFor('unknown');const r=await agent.get('/api/recommendations/nutrition');
  expect(r.status).toBe(200);expect(r.body.data.source).toBe('hybrid');expect(r.body.data.ml.confidence).toBe(4);expect(r.body.data.plan.ml_category_applied).toBe('unknown_category');
});

test('AUDIT DEFECT: Gemini prompt still describes observed zeros as no data',()=>{
  const text=buildRecommendationPrompt({allergy_list:[]},{},{avg_sleep:0,avg_water:0,avg_steps:0,avg_exercise_minutes:0,avg_calories:0,count:1});
  expect(text).toContain('Average sleep: no data');expect(text).toContain('Average water: no data');expect(text).toContain('Average calories logged: no data');
});

test('AUDIT DEFECT: LLM narrative can violate vegan preference despite catalog filtering',async()=>{
  env.aiProvider='gemini';env.geminiApiKey='synthetic-test-key';const base=spy.getMockImplementation();
  spy.mockImplementation(async(url,options)=>url.includes('generativelanguage.googleapis.com') ? response({candidates:[{content:{parts:[{text:JSON.stringify({summary:'Synthetic fixture.',nutrition:[{title:'Chicken',description:'Chicken with cheese.',priority:'medium'}]})}]}}]}) : base(url,options));
  const agent=await agentFor('diet');await agent.put('/api/profile').send({...global.VALID_PROFILE,food_preference:'vegan',allergies:['milk']});
  const r=await agent.get('/api/recommendations/nutrition');expect(r.status).toBe(200);
  expect(r.body.data.llm_recommendations.nutrition[0].title).toBe('Chicken');
  expect(Object.values(r.body.data.plan.meals).flatMap(m=>m.items).every(i=>i.vegan)).toBe(true);
});
