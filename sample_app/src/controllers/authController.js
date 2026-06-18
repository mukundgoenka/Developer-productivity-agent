// Auth controller. The password-reset flow is intentionally split across the
// token service (mint/verify), the email service (deliver the link) and the
// User model (persist the new hash), so it has to be *traced* across files.
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');

const User = require('../models/user');
const tokenService = require('../services/tokenService');
const emailService = require('../services/emailService');

const JWT_SECRET = process.env.JWT_SECRET || 'dev-secret';
const BCRYPT_ROUNDS = 12;

async function login(req, res) {
  const { email, password } = req.body || {};
  const user = await User.findByEmail(email);
  if (!user || !(await bcrypt.compare(password, user.passwordHash))) {
    return res.status(401).json({ error: 'invalid_credentials' });
  }
  const token = jwt.sign({ sub: user.id, role: user.role }, JWT_SECRET, {
    expiresIn: '1h',
  });
  return res.json({ token });
}

// --- Password reset, step 1 --------------------------------------------------
// Always returns 200 even if the email is unknown, so the endpoint can't be
// used to enumerate which addresses have accounts.
async function requestPasswordReset(req, res) {
  const { email } = req.body || {};
  const user = await User.findByEmail(email);
  if (user) {
    const rawToken = await tokenService.createResetToken(user.id);
    await emailService.sendPasswordResetEmail(user.email, rawToken);
  }
  return res.json({ ok: true, message: 'If that account exists, a reset link was sent.' });
}

// --- Password reset, step 2 --------------------------------------------------
async function resetPassword(req, res) {
  const { token, newPassword } = req.body || {};
  if (!token || !newPassword) {
    return res.status(400).json({ error: 'token_and_password_required' });
  }
  const record = await tokenService.verifyResetToken(token);
  if (!record) {
    return res.status(400).json({ error: 'invalid_or_expired_token' });
  }
  const passwordHash = await bcrypt.hash(newPassword, BCRYPT_ROUNDS);
  await User.updatePassword(record.userId, passwordHash);
  await tokenService.consumeResetToken(record.id); // single-use
  return res.json({ ok: true });
}

module.exports = { login, requestPasswordReset, resetPassword };
