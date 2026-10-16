const { User, UserProfile } = require('../models');
const { authenticate, registerUser } = require('../services/authService');
const { created, success } = require('../utils/responses');
const { AuthError } = require('../utils/errors');
const { currentUserId, loginUser, logoutUser } = require('../utils/security');
const { requireJson, validateRequired } = require('../utils/validators');
const { asyncHandler } = require('../middleware/validation');

const register = asyncHandler(async (req, res) => {
  const data = requireJson(req.body);
  validateRequired(data, ['name', 'email', 'password']);
  const user = await registerUser(data.name, data.email, data.password);
  await loginUser(req, user._id);
  return created(res, user.toPublic(false), 'Account created successfully.');
});

const login = asyncHandler(async (req, res) => {
  const data = requireJson(req.body);
  validateRequired(data, ['email', 'password']);
  const user = await authenticate(data.email, data.password);
  await loginUser(req, user._id);
  const profile = await UserProfile.findOne({ userId: user._id });
  return success(res, user.toPublic(Boolean(profile)), 'Signed in.');
});

const logout = asyncHandler(async (req, res) => {
  await logoutUser(req);
  res.clearCookie('connect.sid');
  return success(res, null, 'Signed out.');
});

const me = asyncHandler(async (req, res) => {
  const user = await User.findById(currentUserId(req));
  if (!user) {
    await logoutUser(req);
    res.clearCookie('connect.sid');
    throw new AuthError('User account not found. Please sign in again.');
  }
  const profile = await UserProfile.findOne({ userId: user._id });
  return success(res, user.toPublic(Boolean(profile)));
});

module.exports = { register, login, logout, me };
