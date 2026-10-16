// Read-only audit: synthetic inputs using the application's actual feature builder.
const {computeHealthMetrics}=require('../../backend/src/services/healthMetricsService');
const {buildMlFeatures}=require('../../backend/src/services/featureBuilder');
const {env}=require('../../backend/src/config/env');
const profile={age:30,gender:'male',height_cm:175,weight_kg:70,activity_level:'moderate',goal:'general_wellness',food_preference:'vegetarian',allergy_list:['peanut'],dislike_list:[],sleep_hours:8,water_intake_ml:2800,stress_level:3};
const metrics=computeHealthMetrics(profile);
const summary={avg_sleep:8,avg_water:metrics.water_target_ml,avg_exercise_minutes:30,avg_steps:8000,avg_calories:metrics.calorie_target,avg_stress:3};
const specs=[['baseline',{},{}],['sleep_5h',{}, {avg_sleep:5}],['sleep_7h',{}, {avg_sleep:7}],['water_800ml',{}, {avg_water:800}],['exercise_0min',{}, {avg_exercise_minutes:0}],['steps_1000',{}, {avg_steps:1000}],['goal_fitness',{goal:'improve_fitness'},{}],['weight_95kg',{weight_kg:95},{}],['age_55',{age:55},{}],['stress_5',{stress_level:5},{}]];
specs.push(['low_movement',{}, {avg_exercise_minutes:0,avg_steps:1000}]); // Compare with exercise_0min: only steps changes.
const rows=specs.map(([id,p,s])=>{const pp={...profile,...p},ss={...summary,...s},mm=computeHealthMetrics(pp);return {id,comparison_parent:id==='low_movement'?'exercise_0min':'baseline',changed_profile:p,changed_summary:s,profile:pp,summary:ss,metrics:mm,features:buildMlFeatures(pp,mm,ss)};});
console.log(JSON.stringify({backend:{port:env.port,mlServiceUrl:env.mlServiceUrl,mlEnabled:env.mlEnabled,mlTimeoutMs:env.mlTimeoutMs},rows}));
