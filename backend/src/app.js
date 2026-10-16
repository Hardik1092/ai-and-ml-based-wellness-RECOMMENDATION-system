const express = require('express');
const cors = require('cors');
const session = require('express-session');
const MongoStore = require('connect-mongo');
const { env } = require('./config/env');
const { errorHandler } = require('./middleware/errorHandler');
const { DISCLAIMER } = require('./utils/constants');
const { requireAuth } = require('./middleware/auth');
const { foods } = require('./controllers/nutritionController');
const { activities: listActivities } = require('./controllers/activityController');
const { wellnessScore } = require('./controllers/wellnessController');

const authRoutes = require('./routes/authRoutes');
const profileRoutes = require('./routes/profileRoutes');
const healthRoutes = require('./routes/healthRoutes');
const { recommendationRoutes } = require('./routes/nutritionRoutes');
const dashboardRoutes = require('./routes/dashboardRoutes');
const feedbackRoutes = require('./routes/feedbackRoutes');
const mlRoutes = require('./routes/mlRoutes');
const assistantRoutes = require('./routes/assistantRoutes');
const logRoutes = require('./routes/logRoutes');
const { apiLimiter } = require('./middleware/rateLimiter');

function createApp({ sessionStore } = {}) {
  const app = express();
  app.set('trust proxy', 1);

  // Security Headers
  app.use((_req, res, next) => {
    res.setHeader('X-Content-Type-Options', 'nosniff');
    res.setHeader('X-Frame-Options', 'DENY');
    res.setHeader('X-XSS-Protection', '1; mode=block');
    res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
    next();
  });

  app.use(express.json({ limit: '1mb' }));
  app.use(cors({
    origin: env.corsOrigins,
    credentials: true,
  }));

  const sessionOptions = {
    secret: env.sessionSecret,
    resave: false,
    saveUninitialized: false,
    cookie: {
      httpOnly: true,
      sameSite: 'lax',
      secure: env.sessionCookieSecure,
      maxAge: env.sessionTimeoutMinutes * 60 * 1000,
    },
  };
  if (sessionStore) sessionOptions.store = sessionStore;
  else if (env.nodeEnv !== 'test') {
    sessionOptions.store = MongoStore.create({
      mongoUrl: env.mongoUri,
      collectionName: 'sessions',
    });
  }
  app.use(session(sessionOptions));
  if (env.nodeEnv !== 'test') {
    app.use('/api', apiLimiter);
  }

  app.get('/api/health', (_req, res) => {
    res.json({ success: true, message: 'API is running', disclaimer: DISCLAIMER });
  });

  app.use('/api/auth', authRoutes);
  app.use('/api/profile', profileRoutes);
  app.use('/api/health-metrics', healthRoutes);
  app.use('/api/recommendations', recommendationRoutes);
  app.get('/api/foods', requireAuth, foods);
  app.get('/api/activities', requireAuth, listActivities);
  app.use('/api/logs', logRoutes);
  app.get('/api/wellness-score', requireAuth, wellnessScore);
  app.use('/api/dashboard', dashboardRoutes);
  app.use('/api/feedback', feedbackRoutes);
  app.use('/api/ml', mlRoutes);
  app.use('/api/assistant', assistantRoutes);

  app.use(errorHandler);
  return app;
}

module.exports = { createApp };
