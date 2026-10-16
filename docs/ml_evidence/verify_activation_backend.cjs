// Real HTTP Express -> real HTTP FastAPI, with a disposable MongoDB only.
const path=require('path'),fs=require('fs'),assert=require('assert');
const backend=path.resolve(__dirname,'../../backend');
const {createRequire}=require('module');const req=createRequire(path.join(backend,'package.json'));
const {MongoMemoryServer}=req('mongodb-memory-server');
const mongoose=req('mongoose'),request=req('supertest');
const {env}=require('../../backend/src/config/env');
env.openaiApiKey='';env.geminiApiKey='';env.llamaApiUrl='';
env.nodeEnv='test';env.sessionCookieSecure=false;
const {createApp}=require('../../backend/src/app');
const {seedFoods,seedActivities}=require('../../backend/src/seed/seed');
const {computeHealthMetrics}=require('../../backend/src/services/healthMetricsService');
let mongo,server;
(async()=>{
 assert(env.mlEnabled && env.mlServiceUrl==='http://127.0.0.1:8000');
 mongo=await MongoMemoryServer.create();env.mongoUri=mongo.getUri();
 await mongoose.connect(env.mongoUri);await seedFoods();await seedActivities();
 server=await new Promise(resolve=>{const s=createApp().listen(0,'127.0.0.1',()=>resolve(s));});
 const url=`http://127.0.0.1:${server.address().port}`,agent=request.agent(url);
 const reg=await agent.post('/api/auth/register').send({name:'Synthetic activation audit',email:'activation-audit@example.test',password:'SyntheticAuditOnly2026!'});assert.equal(reg.status,201);
 const profile={age:30,gender:'male',height_cm:175,weight_kg:70,activity_level:'moderate',goal:'general_wellness',food_preference:'vegetarian',allergies:['peanut'],sleep_hours:8,stress_level:3,water_intake_ml:2950};
 const metrics=computeHealthMetrics(profile);
 const base={date:new Date().toISOString().slice(0,10),sleep:8,water:metrics.water_target_ml,exercise_minutes:30,steps:8000,calories:metrics.calorie_target,stress:3,mood:4};
 const output={backend_url:url,ml_url:env.mlServiceUrl,database:'disposable MongoMemoryServer; no production connection',llm:'disabled only in this verification process',prediction_override:false,rows:[]};
 const scenarios=[['baseline',{},{}],['sleep_5h',{}, {sleep:5}],['water_800ml',{}, {water:800}],['exercise_0min',{}, {exercise_minutes:0}],['low_movement',{}, {exercise_minutes:0,steps:1000}],['profile_sleep_5h',{sleep_hours:5},{sleep:null}],['profile_goal_fitness',{goal:'improve_fitness'},{}],['vegan_allergy',{food_preference:'vegan',allergies:['milk','peanut','egg','fish','shellfish','tree_nut','soy','gluten']},{}]];
 for(const [id,p,l] of scenarios){
   const pr=await agent.put('/api/profile').send({...profile,...p});assert.equal(pr.status,200,JSON.stringify(pr.body));
   const lr=await agent.post('/api/logs').send({...base,...l});assert([200,201].includes(lr.status),JSON.stringify(lr.body));
   const nr=await agent.get('/api/recommendations/nutrition');const ar=await agent.get('/api/recommendations/activity');
   assert.equal(nr.status,200,JSON.stringify(nr.body));assert.equal(ar.status,200,JSON.stringify(ar.body));
   for(const d of [nr.body.data,ar.body.data]){assert(d.ml.available);assert.equal(d.ml.model_type,'HistGradientBoostingClassifier');assert.equal(d.source,'hybrid');assert.equal(d.plan.ml_category_applied,d.ml.category);}
   const n=nr.body.data,a=ar.body.data;
   if(id==='vegan_allergy') for(const item of Object.values(n.plan.meals).flatMap(m=>m.items)){assert(item.vegan);assert(!item.allergen_tags.some(t=>profile.allergies.concat(p.allergies).includes(t)));}
   output.rows.push({id,profile_changes:p,log_changes:l,profile_response:pr.body.data,log_response:lr.body.data,nutrition:n,activity:a});
 }
 const low=output.rows.find(r=>r.id==='low_movement');assert.equal(low.activity.ml.category,'activity_focus');
 assert.equal(output.rows.find(r=>r.id==='sleep_5h').nutrition.ml.category,'sleep_focus');
 assert.equal(output.rows.find(r=>r.id==='profile_goal_fitness').nutrition.ml.category,'fitness_improvement');
 // Same profile and data, only disable ML in this isolated process for a causal control.
 env.mlEnabled=false;
 await agent.put('/api/profile').send(profile);await agent.post('/api/logs').send({...base,exercise_minutes:0,steps:1000});
 const control=await agent.get('/api/recommendations/activity');assert.equal(control.status,200);assert.equal(control.body.data.source,'rules_only');
 output.activity_null_control=control.body.data;
 assert.notDeepEqual(low.activity.plan.activities.map(a=>a.activity_name),control.body.data.plan.activities.map(a=>a.activity_name));
 output.passed=true;
 fs.writeFileSync(path.join(__dirname,'activation_backend.json'),JSON.stringify(output,null,2));
 console.log(JSON.stringify({passed:true,backend_url:url,profiles:output.rows.map(r=>({id:r.id,category:r.nutrition.ml.category,probability:r.nutrition.ml.confidence,activities:r.activity.plan.activities.map(a=>a.activity_name)})),null_control:control.body.data.plan.activities.map(a=>a.activity_name)},null,2));
})().catch(e=>{console.error(e.stack);process.exitCode=1;}).finally(async()=>{if(server)await new Promise(resolve=>server.close(resolve));await mongoose.disconnect();if(mongo)await mongo.stop();});
