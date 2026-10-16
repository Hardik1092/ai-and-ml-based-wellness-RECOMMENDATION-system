function createRateLimiter({ windowMs = 60000, max = 30, message = 'Too many requests. Please try again later.' } = {}) {
  const requests = new Map();

  // Periodic cleanup every 5 minutes to prevent memory leak (skip in test environment)
  if (process.env.NODE_ENV !== 'test') {
    setInterval(() => {
      const now = Date.now();
      for (const [key, value] of requests.entries()) {
        if (now > value.resetTime) {
          requests.delete(key);
        }
      }
    }, 5 * 60 * 1000).unref();
  }

  return (req, res, next) => {
    const ip = req.ip || req.headers['x-forwarded-for'] || req.socket.remoteAddress || 'unknown';
    const now = Date.now();
    const entry = requests.get(ip) || { count: 0, resetTime: now + windowMs };

    if (now > entry.resetTime) {
      entry.count = 0;
      entry.resetTime = now + windowMs;
    }

    entry.count += 1;
    requests.set(ip, entry);

    if (entry.count > max) {
      return res.status(429).json({
        success: false,
        message,
        retryAfterMs: Math.max(0, entry.resetTime - now),
      });
    }

    next();
  };
}

const authLimiter = createRateLimiter({ windowMs: 15 * 60 * 1000, max: 50, message: 'Too many authentication attempts. Please try again after 15 minutes.' });
const apiLimiter = createRateLimiter({ windowMs: 60 * 1000, max: 120, message: 'Too many requests. Please slow down.' });
const retrainLimiter = createRateLimiter({ windowMs: 10 * 60 * 1000, max: 5, message: 'Too many retraining requests. Please wait 10 minutes.' });

module.exports = { createRateLimiter, authLimiter, apiLimiter, retrainLimiter };

