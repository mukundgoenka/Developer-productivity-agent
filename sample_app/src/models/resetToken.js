// ResetToken model. Thin wrapper over the `reset_tokens` table.
// Only the token HASH is stored (see tokenService for why).
const db = require('../db/connection');

async function insert({ userId, tokenHash, expiresAt }) {
  const info = db
    .prepare('INSERT INTO reset_tokens (user_id, token_hash, expires_at) VALUES (?, ?, ?)')
    .run(userId, tokenHash, expiresAt);
  return info.lastInsertRowid;
}

async function findByHash(tokenHash) {
  const row = db.prepare('SELECT * FROM reset_tokens WHERE token_hash = ?').get(tokenHash);
  return row ? toToken(row) : null;
}

async function markUsed(id, usedAt) {
  db.prepare('UPDATE reset_tokens SET used_at = ? WHERE id = ?').run(usedAt, id);
}

function toToken(row) {
  return {
    id: row.id,
    userId: row.user_id,
    tokenHash: row.token_hash,
    expiresAt: row.expires_at,
    usedAt: row.used_at,
  };
}

module.exports = { insert, findByHash, markUsed };
