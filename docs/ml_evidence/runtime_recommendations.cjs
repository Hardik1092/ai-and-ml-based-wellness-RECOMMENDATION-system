// Isolated component audit. Only catalog reads are replaced with in-memory seed
// documents in this process. No DB connection, provider call, or application mutation.
const fs=require('fs');
const path=require('path');
const {Food,Activity}=require('../../backend/src/models');
const {FOODS,ACTIVITIES}=require('../../backend/src/seed/seedData');
const {generateNutritionPlan}=require('../../backend/src/services/nutritionService');
const {recommendToday}=require('../../backend/src/services/activityService');
const {dietaryConstraints,isFoodAllowed}=require('../../backend/src/rules/nutritionRules');
const {predictCategory}=require('../../backend/src/services/mlService');
const {buildMlFeatures}=require('../../backend/src/services/featureBuilder');
const audit=JSON.parse(fs.readFileSync(path.join(__dirname,'runtime_audit.json'),'utf8'));
const foods=FOODS.map(([foodName,category,mealType,servingSize,calories,protein,carbohydrates,fat,fiber,vegetarian,vegan,tags,description])=>new Food({foodName,category,mealType,servingSize,calories,protein,carbohydrates,fat,fiber,vegetarian,vegan,allergenTags:tags.split(',').filter(Boolean),description}));
const activities=ACTIVITIES.map(([activityName,category,duration,caloriesBurned,difficulty,intensity,description])=>new Activity({activityName,category,duration,caloriesBurned,difficulty,intensity,description}));
Food.find=async()=>foods;
Activity.find=async(query)=>activities.filter(a=>query.difficulty.$in.includes(a.difficulty));
const categories=[null,...audit.artifacts.configured_runtime.classes];
const mealNames=p=>Object.fromEntries(Object.entries(p.meals).map(([k,v])=>[k,v.items.map(i=>i.food_name)]));
const activityNames=p=>p.activities.map(a=>a.activity_name);
async function plans(row,category){return {nutrition:await generateNutritionPlan(row.profile,row.metrics,dietaryConstraints(row.profile),category),activity:await recommendToday(row.profile,row.metrics,category)};}
(async()=>{
 const output={scope:'Isolated real recommendation functions and real saved-model predictions; seed catalogs held in memory, no production database or live UI',rows:[],safety:[]};
 for(const row of audit.rows){
   const control=await plans(row,null);
   const actual=await plans(row,row.api.category);
   const candidate=await plans(row,row.candidate.category);
   output.rows.push({id:row.id,category:row.api.category,control,actual,candidate,nutrition_selection_changed:JSON.stringify(mealNames(control.nutrition))!==JSON.stringify(mealNames(actual.nutrition)),activity_selection_changed:JSON.stringify(activityNames(control.activity))!==JSON.stringify(activityNames(actual.activity)),meals:mealNames(actual.nutrition),activities:activityNames(actual.activity)});
 }
 for(const pref of ['vegan','vegetarian','non-vegetarian']) for(const allergy of ['peanut','milk','egg','soy','fish','shellfish','gluten','tree_nuts']) for(const cat of categories){
   const row=audit.rows[0],profile={...row.profile,food_preference:pref,allergy_list:[allergy]},constraints=dietaryConstraints(profile);
   const p=await generateNutritionPlan(profile,row.metrics,constraints,cat);
   const selected=Object.values(p.meals).flatMap(m=>m.items);
   const violations=selected.filter(i=>{const f=foods.find(f=>f.foodName===i.food_name);return !isFoodAllowed(f,constraints)[0]||(pref==='vegan'&&!f.vegan)||(pref==='vegetarian'&&!f.vegetarian)||f.allergenTags.includes(allergy);});
   output.safety.push({preference:pref,allergy,category:cat,selected:selected.length,violations:violations.map(v=>v.food_name),excluded_count:p.excluded_count});
 }
 output.sedentary=[];
 for(const cat of categories){const p=await recommendToday({...audit.rows[0].profile,activity_level:'sedentary'},audit.rows[0].metrics,cat);output.sedentary.push({category:cat,difficulties:p.activities.map(a=>a.difficulty)});}
 output.live_backend_ml_client=await predictCategory(audit.rows[0].features);
 const row=audit.rows[0];output.zero_log_behavior={zero_sleep_features:buildMlFeatures(row.profile,row.metrics,{...row.summary,avg_sleep:0}).sleep_hours,zero_water_ratio:buildMlFeatures(row.profile,row.metrics,{...row.summary,avg_water:0}).hydration_ratio,zero_calorie_ratio:buildMlFeatures(row.profile,row.metrics,{...row.summary,avg_calories:0}).calorie_ratio};
 fs.writeFileSync(path.join(__dirname,'runtime_recommendations.json'),JSON.stringify(output,null,2));
 console.log(JSON.stringify({rows:output.rows.map(({id,category,nutrition_selection_changed,activity_selection_changed,meals,activities})=>({id,category,nutrition_selection_changed,activity_selection_changed,meals,activities})),safety_cases:output.safety.length,safety_violations:output.safety.reduce((n,r)=>n+r.violations.length,0),live_backend_ml_client:output.live_backend_ml_client,zero_log_behavior:output.zero_log_behavior},null,2));
})().catch(e=>{console.error(e.message);process.exitCode=1;});
