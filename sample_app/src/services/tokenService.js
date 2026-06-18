// Reset-token service. Tokens are random, single-use and short-lived.
// Security convention: the raw token is emailed to the user but only a SHA-256
// hash is stored at rest, so a leaked DB can't be used to reset passwords.
const crypto = require('crypto');

const ResetToken = require('../models/resetToken');

const RESET_TOKEN_TTL_MINUTES = 30;

function hash(raw) {
  return crypto.createHash('sha256').update(raw).digest('hex');
}

// Returns the RAW token (to email). Only the hash is persisted.
async function createResetToken(userId) {
  const raw = crypto.randomBytes(32).toString('hex');
  const expiresAt = Date.now() + RESET_TOKEN_TTL_MINUTES * 60 * 1000;
  await ResetToken.insert({ userId, tokenHash: hash(raw), expiresAt });
  return raw;
}

// Returns the token record if valid (exists, unused, unexpired), else null.
async function verifyResetToken(raw) {
  const record = await ResetToken.findByHash(hash(raw));
  if (!record) return null;
  if (record.usedAt) return null;
  if (record.expiresAt < Date.now()) return null;
  return record;
}

async function consumeResetToken(id) {
  await ResetToken.markUsed(id, Date.now());
}

module.exports = {
  RESET_TOKEN_TTL_MINUTES,
  createResetToken,
  verifyResetToken,
  consumeResetToken,
};
