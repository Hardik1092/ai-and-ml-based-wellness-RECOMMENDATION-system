const express = require('express');
const { requireAuth } = require('../middleware/auth');
const { retrainLimiter } = require('../middleware/rateLimiter');
const { requireMlAdmin } = require('../middleware/mlAdmin');
const { explanation, retrainFromFeedback } = require('../controllers/mlController');

const router = express.Router();
router.get('/explanation', requireAuth, explanation);
router.post('/retrain', requireAuth, requireMlAdmin, retrainLimiter, retrainFromFeedback);
module.exports = router;
