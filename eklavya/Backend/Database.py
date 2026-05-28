"""
Backend/Database.py
Eklavya SQLite Database Layer — fully organized and production-grade.

Schema:
  users         — id, username, email, phone, password_hash, created_at, last_login
  conversations — id, user_id, session_id, role, content, timestamp
  preferences   — id, user_id, key, value
  sessions      — id, user_id, token, created_at, expires_at

Password hashing: bcrypt (falls back to PBKDF2-SHA256 if bcrypt unavailable)
"""

import sqlite3
import os
import secrets
import hashlib
import datetime
import re

DB_PATH = 'eklavya.db'

# ── Try to import bcrypt (strongest hashing), fallback to PBKDF2 ──────────────
try:
    import bcrypt
    _USE_BCRYPT = True
except ImportError:
    _USE_BCRYPT = False
    print("[Database] bcrypt not installed — using PBKDF2-SHA256 instead. Run: pip install bcrypt")


# ════════════════════════════════════════════════════════════════
#  SCHEMA INIT
# ════════════════════════════════════════════════════════════════

def init_db():
    """Initialize all tables. Safe to call multiple times (uses IF NOT EXISTS)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ── Users ──────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    UNIQUE NOT NULL COLLATE NOCASE,
            email         TEXT    UNIQUE,
            phone         TEXT,
            password_hash TEXT    NOT NULL,
            hash_algo     TEXT    NOT NULL DEFAULT 'pbkdf2',
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login    TIMESTAMP
        )
    ''')

    # ── Conversations (with session grouping) ──────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            session_id TEXT    NOT NULL DEFAULT 'default',
            role       TEXT    NOT NULL CHECK(role IN ('user','assistant','system')),
            content    TEXT    NOT NULL,
            timestamp  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # ── User Preferences (AI mode, language, theme, etc.) ─────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS preferences (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            key     TEXT    NOT NULL,
            value   TEXT    NOT NULL,
            UNIQUE(user_id, key),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # ── Auth Sessions (remember-me tokens) ────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            token      TEXT    UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # ── Indexes for performance (created AFTER migration so columns exist) ──
    # These are safe to repeat — IF NOT EXISTS handles that
    _migrate_columns(cursor)   # ← run migration FIRST so session_id column exists

    try:
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conv_user    ON conversations(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pref_user    ON preferences(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sess_token   ON sessions(token)')
    except Exception as e:
        print(f"[Database] Index creation warning: {e}")

    conn.commit()
    conn.close()
    print("[Database] Initialized successfully.")



def _migrate_columns(cursor):
    """Add new columns to existing databases without breaking them."""
    existing = {row[1] for row in cursor.execute("PRAGMA table_info(users)")}
    migrations = [
        ("email",      "ALTER TABLE users ADD COLUMN email      TEXT"),
        ("phone",      "ALTER TABLE users ADD COLUMN phone      TEXT"),
        ("hash_algo",  "ALTER TABLE users ADD COLUMN hash_algo  TEXT NOT NULL DEFAULT 'pbkdf2'"),
        ("last_login", "ALTER TABLE users ADD COLUMN last_login TIMESTAMP"),
    ]
    for col, sql in migrations:
        if col not in existing:
            try:
                cursor.execute(sql)
            except Exception:
                pass

    # conversations: add session_id if missing
    conv_cols = {row[1] for row in cursor.execute("PRAGMA table_info(conversations)")}
    if 'session_id' not in conv_cols:
        try:
            cursor.execute("ALTER TABLE conversations ADD COLUMN session_id TEXT NOT NULL DEFAULT 'default'")
        except Exception:
            pass


# ════════════════════════════════════════════════════════════════
#  PASSWORD HASHING
# ════════════════════════════════════════════════════════════════

def _hash_password(password: str) -> tuple[str, str]:
    """
    Hash a password securely.
    Returns (hash_string, algo_name).
    Uses bcrypt if available, else PBKDF2-SHA256.
    """
    if _USE_BCRYPT:
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))
        return hashed.decode('utf-8'), 'bcrypt'
    else:
        # PBKDF2-SHA256 with 260,000 iterations (NIST recommended)
        salt = secrets.token_hex(16)
        dk   = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'),
                                    salt.encode('utf-8'), 260000)
        return f"pbkdf2${salt}${dk.hex()}", 'pbkdf2'


def _verify_password(password: str, stored_hash: str, algo: str) -> bool:
    """Verify a password against its stored hash."""
    try:
        if algo == 'bcrypt' and _USE_BCRYPT:
            return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
        elif algo == 'pbkdf2' or stored_hash.startswith('pbkdf2$'):
            parts = stored_hash.split('$')
            if len(parts) == 3:
                _, salt, dk_hex = parts
                dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'),
                                          salt.encode('utf-8'), 260000)
                return secrets.compare_digest(dk.hex(), dk_hex)
        else:
            # Legacy SHA256 (old passwords before this update)
            legacy = hashlib.sha256(password.encode()).hexdigest()
            return secrets.compare_digest(legacy, stored_hash)
    except Exception as e:
        print(f"[Database] Password verify error: {e}")
    return False


# ════════════════════════════════════════════════════════════════
#  VALIDATION HELPERS
# ════════════════════════════════════════════════════════════════

def _is_valid_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(pattern, email))


def _is_valid_phone(phone: str) -> bool:
    # Accept formats like +91XXXXXXXXXX, 91XXXXXXXXXX, 10-digit, etc.
    digits = re.sub(r'\D', '', phone)
    return 7 <= len(digits) <= 15


def validate_registration(username: str, password: str,
                           email: str = None, phone: str = None) -> list[str]:
    """Returns a list of validation error strings. Empty list = valid."""
    errors = []

    if not username or len(username.strip()) < 3:
        errors.append("Username must be at least 3 characters.")
    if not re.match(r'^[a-zA-Z0-9_]+$', username.strip()):
        errors.append("Username can only contain letters, numbers, and underscores.")
    if not password or len(password) < 6:
        errors.append("Password must be at least 6 characters.")

    has_contact = False
    if email and email.strip():
        if not _is_valid_email(email.strip()):
            errors.append("Please enter a valid email address.")
        else:
            has_contact = True
    if phone and phone.strip():
        if not _is_valid_phone(phone.strip()):
            errors.append("Please enter a valid phone number.")
        else:
            has_contact = True
    if not has_contact:
        errors.append("Please provide at least an email or phone number.")

    return errors


# ════════════════════════════════════════════════════════════════
#  USER MANAGEMENT
# ════════════════════════════════════════════════════════════════

def add_user(username: str, password: str,
             email: str = None, phone: str = None) -> dict:
    """
    Register a new user.
    Returns {'success': True, 'user_id': int} or {'success': False, 'error': str}
    """
    username = username.strip()
    email    = email.strip()  if email  else None
    phone    = phone.strip()  if phone  else None

    errors = validate_registration(username, password, email, phone)
    if errors:
        return {'success': False, 'error': ' '.join(errors)}

    pw_hash, algo = _hash_password(password)

    try:
        conn   = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO users (username, email, phone, password_hash, hash_algo) VALUES (?, ?, ?, ?, ?)',
            (username, email, phone, pw_hash, algo)
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        print(f"[Database] User '{username}' registered (id={user_id}, algo={algo})")
        return {'success': True, 'user_id': user_id}
    except sqlite3.IntegrityError as e:
        msg = str(e)
        if 'username' in msg.lower():
            return {'success': False, 'error': 'Username already taken. Choose another.'}
        if 'email' in msg.lower():
            return {'success': False, 'error': 'That email is already registered.'}
        return {'success': False, 'error': 'Account already exists with those details.'}
    except Exception as e:
        return {'success': False, 'error': f'Registration failed: {e}'}


def verify_user(username_or_email: str, password: str) -> dict:
    """
    Verify login credentials. Supports username or email login.
    Returns {'success': True, 'user_id': int, 'username': str} or {'success': False, 'error': str}
    """
    try:
        conn   = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, username, password_hash, hash_algo FROM users WHERE username=? OR email=?',
            (username_or_email.strip(), username_or_email.strip())
        )
        row = cursor.fetchone()

        if not row:
            conn.close()
            return {'success': False, 'error': 'No account found with that username or email.'}

        uid, username, pw_hash, algo = row

        if not _verify_password(password, pw_hash, algo or 'sha256'):
            conn.close()
            return {'success': False, 'error': 'Incorrect password. Please try again.'}

        # Update last_login timestamp
        cursor.execute('UPDATE users SET last_login=CURRENT_TIMESTAMP WHERE id=?', (uid,))
        conn.commit()
        conn.close()
        print(f"[Database] User '{username}' logged in (id={uid})")
        return {'success': True, 'user_id': uid, 'username': username}

    except Exception as e:
        return {'success': False, 'error': f'Login error: {e}'}


def get_user_by_id(user_id: int) -> dict | None:
    """Return user info dict or None."""
    try:
        conn   = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, email, phone, created_at, last_login FROM users WHERE id=?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {'id': row[0], 'username': row[1], 'email': row[2],
                    'phone': row[3], 'created_at': row[4], 'last_login': row[5]}
    except Exception:
        pass
    return None


# ════════════════════════════════════════════════════════════════
#  SESSION TOKENS (Remember Me)
# ════════════════════════════════════════════════════════════════

def create_session(user_id: int, days: int = 30) -> str:
    """Create a secure remember-me token. Returns the token string."""
    token      = secrets.token_urlsafe(48)
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=days)
    try:
        conn   = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Clean old sessions for this user first
        cursor.execute('DELETE FROM sessions WHERE user_id=? AND expires_at < CURRENT_TIMESTAMP', (user_id,))
        cursor.execute('INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)',
                       (user_id, token, expires_at.isoformat()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Database] Session create error: {e}")
    return token


def verify_session(token: str) -> dict | None:
    """
    Validate a remember-me token.
    Returns user dict if valid, None if expired/invalid.
    """
    if not token:
        return None
    try:
        conn   = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT s.user_id, u.username FROM sessions s
               JOIN users u ON u.id = s.user_id
               WHERE s.token=? AND s.expires_at > CURRENT_TIMESTAMP''',
            (token,)
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return {'user_id': row[0], 'username': row[1]}
    except Exception as e:
        print(f"[Database] Session verify error: {e}")
    return None


def delete_session(token: str):
    """Delete a specific session (logout)."""
    try:
        conn   = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM sessions WHERE token=?', (token,))
        conn.commit()
        conn.close()
    except Exception:
        pass


def delete_all_sessions(user_id: int):
    """Logout from all devices."""
    try:
        conn   = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM sessions WHERE user_id=?', (user_id,))
        conn.commit()
        conn.close()
    except Exception:
        pass


# ════════════════════════════════════════════════════════════════
#  CONVERSATION HISTORY
# ════════════════════════════════════════════════════════════════

def save_chat(user_id: int, role: str, content: str, session_id: str = 'default'):
    """Save a single message to the conversations table."""
    try:
        conn   = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO conversations (user_id, session_id, role, content) VALUES (?, ?, ?, ?)',
            (user_id, session_id, role, content)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Database] Save chat error: {e}")


def load_chats(user_id: int, limit: int = 50, session_id: str = None) -> list:
    """
    Load conversation history for a user.
    If session_id given, load only that session. Otherwise load across all sessions.
    Returns list of {'role': str, 'content': str} dicts in chronological order.
    """
    try:
        conn   = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        if session_id:
            cursor.execute(
                '''SELECT role, content FROM conversations
                   WHERE user_id=? AND session_id=?
                   ORDER BY timestamp DESC LIMIT ?''',
                (user_id, session_id, limit)
            )
        else:
            cursor.execute(
                '''SELECT role, content FROM conversations
                   WHERE user_id=?
                   ORDER BY timestamp DESC LIMIT ?''',
                (user_id, limit)
            )
        rows = cursor.fetchall()
        conn.close()
        return [{'role': r[0], 'content': r[1]} for r in reversed(rows)]
    except Exception as e:
        print(f"[Database] Load chats error: {e}")
        return []


def clear_chats(user_id: int, session_id: str = None):
    """Clear conversation history for a user (optionally just one session)."""
    try:
        conn   = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        if session_id:
            cursor.execute('DELETE FROM conversations WHERE user_id=? AND session_id=?', (user_id, session_id))
        else:
            cursor.execute('DELETE FROM conversations WHERE user_id=?', (user_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Database] Clear chats error: {e}")


# ════════════════════════════════════════════════════════════════
#  PREFERENCES
# ════════════════════════════════════════════════════════════════

def set_preference(user_id: int, key: str, value: str):
    """Upsert a user preference (e.g. ai_mode='gemini')."""
    try:
        conn   = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO preferences (user_id, key, value) VALUES (?, ?, ?)',
            (user_id, key, value)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Database] Set preference error: {e}")


def get_preference(user_id: int, key: str, default: str = None) -> str | None:
    """Get a user preference."""
    try:
        conn   = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM preferences WHERE user_id=? AND key=?', (user_id, key))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else default
    except Exception:
        return default


# ════════════════════════════════════════════════════════════════
#  DB STATISTICS (for admin/UI display)
# ════════════════════════════════════════════════════════════════

def get_db_stats() -> dict:
    """Return summary statistics about the database."""
    try:
        conn   = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        users = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM conversations')
        messages = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(DISTINCT user_id) FROM conversations')
        active_users = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM sessions WHERE expires_at > CURRENT_TIMESTAMP')
        active_sessions = cursor.fetchone()[0]
        db_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
        conn.close()
        return {
            'users':           users,
            'messages':        messages,
            'active_users':    active_users,
            'active_sessions': active_sessions,
            'db_size_kb':      round(db_size / 1024, 1),
        }
    except Exception as e:
        print(f"[Database] Stats error: {e}")
        return {}


# ════════════════════════════════════════════════════════════════
#  LEGACY MIGRATION
# ════════════════════════════════════════════════════════════════

def migrate_json_data(user_id: int, json_path: str = 'ChatLog.json'):
    """Import messages from the old JSON log into the SQL database."""
    if not os.path.exists(json_path):
        return
    try:
        import json
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list) and data:
            conn   = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            for msg in data:
                role    = msg.get('role', 'user')
                content = msg.get('content', '')
                if content:
                    cursor.execute(
                        'INSERT INTO conversations (user_id, session_id, role, content) VALUES (?, ?, ?, ?)',
                        (user_id, 'imported', role, content)
                    )
            conn.commit()
            conn.close()
            print(f"[Database] Migrated {len(data)} messages from JSON.")
    except Exception as e:
        print(f"[Database] Migration error: {e}")
