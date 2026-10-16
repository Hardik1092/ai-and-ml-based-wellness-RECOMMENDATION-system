const { AppError } = require('../utils/errors');
const { env } = require('../config/env');

function errorHandler(err, _req, res, _next) {
  if (err instanceof AppError) {
    const body = { success: false, message: err.message, error: err.errorCode };
    if (err.details && Object.keys(err.details).length) body.details = err.details;
    return res.status(err.statusCode).json(body);
  }

  if (err.name === 'ValidationError' && err.errors) {
    return res.status(422).json({
      success: false,
      message: 'Unable to process the request.',
      error: 'VALIDATION_ERROR',
    });
  }

  if (err.name === 'CastError') {
    return res.status(400).json({
      success: false,
      message: `Invalid identifier format: ${err.path || 'id'}.`,
      error: 'INVALID_ID',
    });
  }

  console.error('Unhandled application error:', err && err.message);
  if (env.nodeEnv !== 'production' && env.nodeEnv !== 'test') {
    console.error(err);
  }
  return res.status(500).json({
    success: false,
    message: 'Something went wrong on our side. Please try again.',
    error: 'INTERNAL_ERROR',
  });
}

module.exports = { errorHandler };
