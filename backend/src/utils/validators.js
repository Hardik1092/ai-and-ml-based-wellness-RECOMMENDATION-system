const { ACTIVITY_LEVELS, FOOD_PREFERENCES, GENDERS, GOALS } = require('./constants');
const { ValidationError } = require('./errors');

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$/;

const BOUNDS = {
  age: [10, 100, 'Age must be between 10 and 100.'],
  height_cm: [90, 250, 'Height must be between 90 and 250 cm.'],
  weight_kg: [25, 300, 'Weight must be between 25 and 300 kg.'],
  sleep_hours: [0, 24, 'Sleep hours must be between 0 and 24.'],
  sitting_hours: [0, 24, 'Sitting hours must be between 0 and 24.'],
  water_intake_ml: [0, 10000, 'Water intake must be between 0 and 10000 ml.'],
  stress_level: [1, 5, 'Stress level must be between 1 and 5.'],
  mood: [1, 5, 'Mood must be between 1 and 5.'],
  meal_frequency: [1, 8, 'Meal frequency must be between 1 and 8.'],
  steps: [0, 100000, 'Steps must be between 0 and 100000.'],
  exercise_minutes: [0, 1440, 'Exercise minutes must be between 0 and 1440.'],
  rating: [1, 5, 'Rating must be between 1 and 5.'],
};

function requireJson(payload) {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    throw new ValidationError('A JSON request body is required.');
  }
  return payload;
}

function validateRequired(data, fields) {
  const missing = fields.filter((f) => data[f] === undefined || data[f] === null || data[f] === '');
  if (missing.length) {
    throw new ValidationError(
      `Please fill in all required fields: ${missing.join(', ')}`,
      { missing },
    );
  }
}

function validateEmail(value) {
  const email = String(value || '').trim().toLowerCase();
  if (!EMAIL_RE.test(email)) {
    throw new ValidationError('Please enter a valid email address.');
  }
  return email;
}

function validatePassword(value) {
  if (!value || String(value).length < 8) {
    throw new ValidationError('Password must be at least 8 characters long.');
  }
  if (!/[A-Za-z]/.test(value) || !/\d/.test(value)) {
    throw new ValidationError('Password must contain at least one letter and one number.');
  }
  return value;
}

function validateName(value) {
  const name = String(value || '').trim();
  if (name.length < 2 || name.length > 80) {
    throw new ValidationError('Name must be between 2 and 80 characters.');
  }
  return name;
}

function validateNumber(value, field, required = true) {
  if (value === undefined || value === null || value === '') {
    if (required) {
      throw new ValidationError(`${field.replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase())} is required.`);
    }
    return null;
  }
  const number = Number(value);
  if (typeof value === 'boolean' || typeof value === 'object' || !Number.isFinite(number)) {
    throw new ValidationError(`${field.replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase())} must be a number.`);
  }
  if (BOUNDS[field]) {
    const [low, high, message] = BOUNDS[field];
    if (!(low <= number && number <= high)) throw new ValidationError(message);
  }
  return number;
}

function validateInt(value, field, required = true) {
  const number = validateNumber(value, field, required);
  return number === null ? null : Math.round(number);
}

function validateChoice(value, field, allowed, required = true) {
  if (value === undefined || value === null || value === '') {
    if (required) {
      throw new ValidationError(`${field.replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase())} is required.`);
    }
    return null;
  }
  const normalised = String(value).trim().toLowerCase().replace(/ /g, '_');
  if (!allowed.includes(normalised)) {
    throw new ValidationError(
      `${field.replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase())} must be one of: ${allowed.join(', ')}.`,
    );
  }
  return normalised;
}

function validateActivityLevel(value, required = true) {
  return validateChoice(value, 'activity_level', ACTIVITY_LEVELS, required);
}

function validateFoodPreference(value, required = true) {
  let next = String(value || '').trim().toLowerCase().replace(/ /g, '-').replace(/_/g, '-');
  if (next === 'nonvegetarian') next = 'non-vegetarian';
  return validateChoice(next, 'food_preference', FOOD_PREFERENCES, required);
}

function validateGoal(value, required = true) {
  return validateChoice(value, 'goal', GOALS, required);
}

function validateGender(value, required = true) {
  return validateChoice(value, 'gender', GENDERS, required);
}

function validateDate(value, required = true) {
  if (value === undefined || value === null || value === '') {
    if (required) throw new ValidationError('Date is required.');
    return null;
  }
  if (value instanceof Date && !Number.isNaN(value.getTime())) {
    return value.toISOString().slice(0, 10);
  }
  const text = String(value).slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(text)) {
    throw new ValidationError('Date must be in YYYY-MM-DD format.');
  }
  const parsed = new Date(`${text}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) {
    throw new ValidationError('Date must be in YYYY-MM-DD format.');
  }
  return text;
}

function normaliseTagList(value) {
  if (!value) return [];
  let parts;
  if (typeof value === 'string') {
    parts = value.split(/[,;\n]/);
  } else if (Array.isArray(value)) {
    parts = value.map((p) => String(p));
  } else {
    throw new ValidationError('Expected a list or comma-separated text.');
  }
  const unique = new Set(
    parts.map((p) => p.trim().toLowerCase().replace(/ /g, '_')).filter(Boolean),
  );
  return Array.from(unique).sort();
}

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

module.exports = {
  EMAIL_RE,
  BOUNDS,
  requireJson,
  validateRequired,
  validateEmail,
  validatePassword,
  validateName,
  validateNumber,
  validateInt,
  validateChoice,
  validateActivityLevel,
  validateFoodPreference,
  validateGoal,
  validateGender,
  validateDate,
  normaliseTagList,
  todayIso,
};
