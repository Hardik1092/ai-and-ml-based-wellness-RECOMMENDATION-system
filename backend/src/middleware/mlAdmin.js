const { env } = require('../config/env');

function requireMlAdmin(req, res, next) {
  const userId = String(req.session?.userId || '');
  if (!env.mlAdminUserIds.includes(userId)) {
    return res.status(403).json({ success: false, message: 'ML training requires an explicitly configured administrator.' });
  }
  return next();
}

module.exports = { requireMlAdmin };
