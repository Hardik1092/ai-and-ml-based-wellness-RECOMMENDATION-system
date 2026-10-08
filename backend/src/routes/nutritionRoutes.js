const express = require('express');
const { requireAuth } = require('../middleware/auth');
const { nutrition, foods } = require('../controllers/nutritionController');
const { today, weekly, activities } = require('../controllers/activityController');
const { wellness } = require('../controllers/wellnessController');
const { recent } = require('../controllers/feedbackController');

const router = express.Router();
router.get('/nutrition', requireAuth, nutrition);
router.get('/daily', requireAuth, nutrition);
router.get('/activity/weekly', requireAuth, weekly);
router.get('/activity', requireAuth, today);
router.get('/wellness', requireAuth, wellness);
router.get('/recent', requireAuth, recent);
module.exports = { recommendationRoutes: router, foods, activities };
