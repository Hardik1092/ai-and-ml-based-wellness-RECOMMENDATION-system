/**
 * Deterministic medical safety guidelines.
 * These safety constraints operate unconditionally in the deterministic engine,
 * guaranteeing that recorded chronic conditions protect the user even without an LLM.
 */

function medicalRules(profile, metrics) {
  const mh = profile.medical_history || {};
  if (!mh.has_conditions && (!mh.conditions || !mh.conditions.length)) {
    return [];
  }

  const conditions = mh.conditions || [];
  const rules = [];

  const condText = conditions.join(' ').toLowerCase();

  if (condText.includes('diabetes')) {
    rules.push({
      code: 'MED_DIABETES_GUARD',
      area: 'nutrition',
      priority: 1,
      message: 'Glycemic safety: Prioritizing complex unrefined grains, legumes, and high-fiber foods to support steady blood glucose.',
      reason: 'Diagnosed Diabetes reported on your wellness profile.',
    });
  }

  if (condText.includes('hypertension') || condText.includes('blood pressure')) {
    rules.push({
      code: 'MED_HYPERTENSION_GUARD',
      area: 'nutrition',
      priority: 1,
      message: 'Cardiovascular balance: Emphasizing potassium-rich vegetables, consistent hydration, and lower-sodium whole foods.',
      reason: 'Diagnosed Hypertension reported on your profile.',
    });
    rules.push({
      code: 'MED_HYPERTENSION_ACTIVITY',
      area: 'activity',
      priority: 1,
      message: 'Blood pressure guidance: Favouring rhythmic aerobic exercise and moderate walking over prolonged heavy isometric strain.',
      reason: 'Hypertension exercise safety parameter active.',
    });
  }

  if (condText.includes('cholesterol') || condText.includes('heart disease')) {
    rules.push({
      code: 'MED_LIPID_GUARD',
      area: 'nutrition',
      priority: 1,
      message: 'Lipid balance: Promoting soluble fiber sources (oats, beans, lentils) and heart-healthy unsaturated plant lipids.',
      reason: 'Cholesterol / Heart condition recorded on your profile.',
    });
  }

  if (condText.includes('kidney')) {
    rules.push({
      code: 'MED_RENAL_GUARD',
      area: 'nutrition',
      priority: 1,
      message: 'Renal moderation: High-protein surplus targets are capped to prevent unnecessary glomerular filtration stress.',
      reason: 'Diagnosed Kidney condition reported on your profile.',
    });
  }

  if (condText.includes('asthma')) {
    rules.push({
      code: 'MED_RESPIRATORY_GUARD',
      area: 'activity',
      priority: 1,
      message: 'Respiratory pacing: Ensure adequate warm-ups and avoid sudden maximum-intensity sprints.',
      reason: 'Asthma reported on your profile.',
    });
  }

  if (mh.medications && mh.medications.length) {
    rules.push({
      code: 'MED_PRESCRIBED_NOTE',
      area: 'wellness',
      priority: 1,
      message: 'Prescription safety: Wellness guidance is general educational support and must not replace or modify your prescribed medication schedule.',
      reason: 'Active prescription medications noted on profile.',
    });
  }

  return rules;
}

module.exports = { medicalRules };
