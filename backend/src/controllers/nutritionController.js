const { Food } = require('../models');
const { getProfile } = require('../services/profileService');
const { nutritionRecommendation } = require('../services/recommendationService');
const { storeRecommendation } = require('../services/recommendationStore');
const { DISCLAIMER } = require('../utils/constants');
const { success } = require('../utils/responses');
const { currentUserId } = require('../utils/security');
const { asyncHandler } = require('../middleware/validation');

const nutrition = asyncHandler(async (req, res) => {
  const userId = currentUserId(req);
  const profile = await getProfile(userId);
  const result = await nutritionRecommendation(userId, profile);
  const record = await storeRecommendation(userId, 'nutrition', result);
  return success(res, { ...result, recommendation_id: String(record._id), disclaimer: DISCLAIMER });
});

const foods = asyncHandler(async (req, res) => {
  const filter = {};
  if (req.query.meal_type) filter.mealType = req.query.meal_type;
  if (req.query.category) filter.category = req.query.category;
  const limit = Math.min(Number(req.query.limit || 200), 500);
  const items = await Food.find(filter).sort({ foodName: 1 }).limit(limit);
  return success(res, items.map((f) => f.toPublic()), `${items.length} foods.`);
});

module.exports = { nutrition, foods };
