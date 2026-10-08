const { activityRules } = require('./activityRules');
const { bmiRules } = require('./bmiRules');
const { medicalRules } = require('./medicalRules');
const { dietaryConstraints, nutritionRules } = require('./nutritionRules');
const { wellnessRules } = require('./wellnessRules');

function evaluateRules(profile, metrics, logs = []) {
  const fired = [
    ...medicalRules(profile, metrics),
    ...bmiRules(metrics),
    ...nutritionRules(metrics, profile),
    ...activityRules(metrics, profile),
    ...wellnessRules(logs, metrics, profile),
  ];
  fired.sort((a, b) => a.priority - b.priority);
  return {
    constraints: dietaryConstraints(profile),
    rules: fired,
    by_area: {
      nutrition: fired.filter((r) => r.area === 'nutrition'),
      activity: fired.filter((r) => r.area === 'activity'),
      wellness: fired.filter((r) => r.area === 'wellness'),
    },
  };
}

module.exports = { evaluateRules };
