const { MEAL_CALORIE_SPLIT } = require('../utils/constants');

function dietaryConstraints(profile) {
  return {
    food_preference: profile.food_preference,
    excluded_allergens: profile.allergy_list || [],
    disliked: profile.dislike_list || [],
  };
}

function isFoodAllowed(food, constraints) {
  const pref = constraints.food_preference;
  const vegan = Boolean(food.vegan);
  const vegetarian = Boolean(food.vegetarian);
  const allergens = (food.allergenTags || food.allergens || []).map((t) => String(t).toLowerCase().trim());
  const name = String(food.foodName || food.food_name || '').toLowerCase();
  const desc = String(food.description || '').toLowerCase();
  const category = String(food.category || '').toLowerCase();

  if (pref === 'vegan' && !vegan) return [false, 'not vegan'];
  if (pref === 'vegetarian' && !vegetarian) return [false, 'contains meat or fish'];

  const excluded = (constraints.excluded_allergens || []).map((a) => String(a).toLowerCase().trim());
  for (const allergy of excluded) {
    if (!allergy) continue;
    // Direct allergen tag match
    if (allergens.includes(allergy)) return [false, `contains allergen: ${allergy}`];
    
    // Dairy / Milk
    if (allergy === 'dairy' || allergy === 'milk') {
      if (allergens.includes('milk') || allergens.includes('dairy') || category === 'dairy' || name.includes('paneer') || name.includes('yogurt') || name.includes('curd')) {
        return [false, 'contains dairy / milk'];
      }
    }
    // Peanut
    if (allergy === 'peanut' || allergy === 'peanuts') {
      if (allergens.includes('peanut') || allergens.includes('peanuts') || name.includes('peanut') || desc.includes('peanut')) {
        return [false, 'contains peanuts'];
      }
    }
    // Tree nuts
    if (allergy === 'tree_nut' || allergy === 'tree_nuts' || allergy === 'nuts') {
      if (allergens.some((a) => a.includes('nut')) || name.includes('nut') || desc.includes('nut') || name.includes('almond') || name.includes('walnut')) {
        return [false, 'contains tree nuts'];
      }
    }
    // Egg
    if (allergy === 'egg' || allergy === 'eggs') {
      if (allergens.includes('egg') || allergens.includes('eggs') || name.includes('egg') || desc.includes('egg') || name.includes('omelette')) {
        return [false, 'contains egg'];
      }
    }
    // Gluten / Wheat
    if (allergy === 'gluten' || allergy === 'wheat') {
      if (allergens.includes('gluten') || allergens.includes('wheat') || name.includes('wheat') || name.includes('roti') || name.includes('thepla') || name.includes('oats') || desc.includes('gluten')) {
        return [false, 'contains gluten / wheat'];
      }
    }
    // Soy
    if (allergy === 'soy' || allergy === 'soya' || allergy === 'soybeans') {
      if (allergens.includes('soy') || allergens.includes('soya') || name.includes('soy') || name.includes('tofu') || desc.includes('soy')) {
        return [false, 'contains soy'];
      }
    }
    // Fish
    if (allergy === 'fish') {
      if (allergens.includes('fish') || name.includes('fish') || desc.includes('fish')) {
        return [false, 'contains fish'];
      }
    }
    // Shellfish
    if (allergy === 'shellfish') {
      if (allergens.includes('shellfish') || allergens.includes('prawn') || name.includes('prawn') || name.includes('shrimp') || desc.includes('prawn')) {
        return [false, 'contains shellfish'];
      }
    }
  }

  for (const disliked of constraints.disliked || []) {
    if (disliked && name.includes(disliked.replace(/_/g, ' ').toLowerCase())) {
      return [false, 'on your dislikes list'];
    }
  }
  return [true, 'allowed'];
}

function mealCalorieBudget(calorieTarget) {
  const out = {};
  for (const [meal, share] of Object.entries(MEAL_CALORIE_SPLIT)) {
    out[meal] = Math.round(calorieTarget * share);
  }
  return out;
}

function nutritionRules(metrics, profile) {
  const out = [];
  const goal = profile.goal;
  if (goal === 'weight_loss') {
    out.push({
      code: 'GOAL_DEFICIT', area: 'nutrition', priority: 1,
      message: `Your daily target of ${metrics.calorie_target} kcal is a moderate ${Math.abs(metrics.calorie_adjustment_pct)}% reduction from your estimated maintenance level.`,
      reason: 'Your goal is weight loss, so a moderate deficit is applied.',
    });
  } else if (goal === 'weight_gain' || goal === 'muscle_building') {
    out.push({
      code: 'GOAL_SURPLUS', area: 'nutrition', priority: 1,
      message: `Your daily target of ${metrics.calorie_target} kcal includes a moderate ${metrics.calorie_adjustment_pct}% surplus, with ${metrics.protein_g} g of protein to support training.`,
      reason: `Your goal is ${goal.replace(/_/g, ' ')}.`,
    });
  } else {
    out.push({
      code: 'GOAL_MAINTAIN', area: 'nutrition', priority: 2,
      message: `Your target of ${metrics.calorie_target} kcal matches your estimated daily energy use.`,
      reason: 'Your goal is to maintain your current weight.',
    });
  }

  if (profile.food_preference === 'vegan') {
    out.push({
      code: 'PREF_VEGAN', area: 'nutrition', priority: 2,
      message: 'Combine pulses, grains and seeds across the day to cover your protein target, and keep an eye on B12 sources.',
      reason: 'Your food preference is set to vegan.',
    });
  }
  if ((profile.allergy_list || []).length) {
    out.push({
      code: 'ALLERGY_FILTER', area: 'nutrition', priority: 1,
      message: `Foods tagged with ${profile.allergy_list.join(', ')} have been removed from every meal.`,
      reason: 'These allergens are recorded on your profile.',
    });
  }
  return out;
}

module.exports = { dietaryConstraints, isFoodAllowed, mealCalorieBudget, nutritionRules };
