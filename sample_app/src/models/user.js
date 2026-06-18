// User model. Thin wrapper over the `users` table (see db/schema.sql).
const db = require('../db/connection');

async function findByEmail(email) {
  const row = db.prepare('SELECT * FROM users WHERE email = ?').get(email);
  return row ? toUser(row) : null;
}

async function findById(id) {
  const row = db.prepare('SELECT * FROM users WHERE id = ?').get(id);
  return row ? toUser(row) : null;
}

async function updatePassword(userId, passwordHash) {
  db.prepare('UPDATE users SET password_hash = ? WHERE id = ?').run(passwordHash, userId);
}

function toUser(row) {
  return {
    id: row.id,
    email: row.email,
    passwordHash: row.password_hash,
    role: row.role,
  };
}

module.exports = { findByEmail, findById, updatePassword };
