import sqlite3
import os
import random
import string
import hashlib

DB_PATH = os.path.join(os.path.dirname(__file__), "ctf.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Progress table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            username TEXT PRIMARY KEY,
            current_stage INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Attempts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            stage INTEGER,
            result TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Answers table for quiz4, quiz5, quiz9
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS answers (
            username TEXT,
            stage INTEGER,
            expected TEXT,
            PRIMARY KEY (username, stage)
        );
    """)

    # Flags table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS flags (
            username TEXT PRIMARY KEY,
            flag TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    conn.close()


# ── Auth helpers ──────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def register_user(username: str, password: str) -> dict:
    """Register a new user. Returns {'ok': True} or {'ok': False, 'error': '...'}"""
    if not username or not password:
        return {"ok": False, "error": "Username va parol bo'sh bo'lishi mumkin emas."}
    if len(username) < 3:
        return {"ok": False, "error": "Username kamida 3 ta belgidan iborat bo'lishi kerak."}
    if len(password) < 4:
        return {"ok": False, "error": "Parol kamida 4 ta belgidan iborat bo'lishi kerak."}
    # Only allow alphanumeric + underscore
    import re
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return {"ok": False, "error": "Username faqat harf, raqam va _ belgilaridan iborat bo'lishi kerak."}

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        conn.close()
        return {"ok": False, "error": f"'{username}' allaqachon mavjud. Boshqa username tanlang."}

    password_hash = hash_password(password)
    cursor.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        (username, password_hash)
    )
    conn.commit()
    conn.close()

    # Initialize progress for new user
    seed_student(username)
    return {"ok": True}


def login_user(username: str, password: str) -> dict:
    """Verify login credentials. Returns {'ok': True} or {'ok': False, 'error': '...'}"""
    if not username or not password:
        return {"ok": False, "error": "Username va parol kiritilishi shart."}

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {"ok": False, "error": "Foydalanuvchi topilmadi."}

    if row["password_hash"] != hash_password(password):
        return {"ok": False, "error": "Parol noto'g'ri."}

    return {"ok": True}


def user_exists(username: str) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return row is not None


# ── Student helpers ───────────────────────────────────────────────────────────

def generate_random_key(prefix="KEY_", length=8):
    chars = string.ascii_uppercase + string.digits
    return prefix + ''.join(random.choices(chars, k=length))


def seed_student(username):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT current_stage FROM progress WHERE username = ?", (username,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO progress (username, current_stage) VALUES (?, 1)", (username,))

    # Quiz 4 answer
    cursor.execute("SELECT expected FROM answers WHERE username = ? AND stage = 4", (username,))
    if not cursor.fetchone():
        key4 = generate_random_key("KEY-")
        cursor.execute("INSERT INTO answers (username, stage, expected) VALUES (?, 4, ?)", (username, key4))

    # Quiz 5 answer
    cursor.execute("SELECT expected FROM answers WHERE username = ? AND stage = 5", (username,))
    if not cursor.fetchone():
        key5 = generate_random_key("PASS-")
        cursor.execute("INSERT INTO answers (username, stage, expected) VALUES (?, 5, ?)", (username, key5))

    # Quiz 9 answer
    cursor.execute("SELECT expected FROM answers WHERE username = ? AND stage = 9", (username,))
    if not cursor.fetchone():
        key9 = generate_random_key("PART-")
        cursor.execute("INSERT INTO answers (username, stage, expected) VALUES (?, 9, ?)", (username, key9))

    # ── CTF 2 Stages (11-20) ─────────────────────────────────
    # Quiz 11
    cursor.execute("SELECT expected FROM answers WHERE username = ? AND stage = 11", (username,))
    if not cursor.fetchone():
        k11 = generate_random_key("SEC11-")
        cursor.execute("INSERT INTO answers (username, stage, expected) VALUES (?, 11, ?)", (username, k11))

    # Quiz 12
    cursor.execute("SELECT expected FROM answers WHERE username = ? AND stage = 12", (username,))
    if not cursor.fetchone():
        k12 = generate_random_key("CONF12-")
        cursor.execute("INSERT INTO answers (username, stage, expected) VALUES (?, 12, ?)", (username, k12))

    # Quiz 13
    cursor.execute("SELECT expected FROM answers WHERE username = ? AND stage = 13", (username,))
    if not cursor.fetchone():
        k13 = "BiGs0Z" + generate_random_key("", length=4)
        cursor.execute("INSERT INTO answers (username, stage, expected) VALUES (?, 13, ?)", (username, k13))

    # Quiz 14
    cursor.execute("SELECT expected FROM answers WHERE username = ? AND stage = 14", (username,))
    if not cursor.fetchone():
        k14 = generate_random_key("LOG14-")
        cursor.execute("INSERT INTO answers (username, stage, expected) VALUES (?, 14, ?)", (username, k14))

    # Quiz 15
    cursor.execute("SELECT expected FROM answers WHERE username = ? AND stage = 15", (username,))
    if not cursor.fetchone():
        k15 = generate_random_key("SIZE15-")
        cursor.execute("INSERT INTO answers (username, stage, expected) VALUES (?, 15, ?)", (username, k15))

    # Quiz 16
    cursor.execute("SELECT expected FROM answers WHERE username = ? AND stage = 16", (username,))
    if not cursor.fetchone():
        k16 = generate_random_key("PERM16-")
        cursor.execute("INSERT INTO answers (username, stage, expected) VALUES (?, 16, ?)", (username, k16))

    # Quiz 17
    cursor.execute("SELECT expected FROM answers WHERE username = ? AND stage = 17", (username,))
    if not cursor.fetchone():
        k17 = generate_random_key("TYPE17-")
        cursor.execute("INSERT INTO answers (username, stage, expected) VALUES (?, 17, ?)", (username, k17))

    # Quiz 18
    cursor.execute("SELECT expected FROM answers WHERE username = ? AND stage = 18", (username,))
    if not cursor.fetchone():
        k18 = generate_random_key("LINE18-")
        cursor.execute("INSERT INTO answers (username, stage, expected) VALUES (?, 18, ?)", (username, k18))

    # Quiz 19
    cursor.execute("SELECT expected FROM answers WHERE username = ? AND stage = 19", (username,))
    if not cursor.fetchone():
        k19 = generate_random_key("CLEAN19-")
        cursor.execute("INSERT INTO answers (username, stage, expected) VALUES (?, 19, ?)", (username, k19))

    # Quiz 20
    cursor.execute("SELECT expected FROM answers WHERE username = ? AND stage = 20", (username,))
    if not cursor.fetchone():
        k20 = generate_random_key("FINAL20-")
        cursor.execute("INSERT INTO answers (username, stage, expected) VALUES (?, 20, ?)", (username, k20))

    conn.commit()
    conn.close()


def get_student_stage(username):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT current_stage FROM progress WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return row["current_stage"] if row else 1


def get_student_answers(username):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT stage, expected FROM answers WHERE username = ?", (username,))
    rows = cursor.fetchall()
    conn.close()
    return {row["stage"]: row["expected"] for row in rows}


def log_attempt(username, stage, result):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO attempts (username, stage, result) VALUES (?, ?, ?)",
        (username, stage, result)
    )
    conn.commit()
    conn.close()


def get_stage_fail_count(username, stage):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) as cnt FROM attempts WHERE username = ? AND stage = ? AND result = 'fail'",
        (username, stage)
    )
    row = cursor.fetchone()
    conn.close()
    return row["cnt"] if row else 0


def update_student_stage(username, next_stage):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE progress SET current_stage = ?, updated_at = CURRENT_TIMESTAMP WHERE username = ?",
        (next_stage, username)
    )
    conn.commit()
    conn.close()


def save_student_flag(username, flag, level=1):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT flag FROM flags WHERE username = ?", (username,))
    row = cursor.fetchone()
    if row and row["flag"]:
        existing = row["flag"]
        if flag not in existing:
            new_flag = f"{existing} | {flag}"
        else:
            new_flag = existing
    else:
        new_flag = flag

    cursor.execute(
        "INSERT OR REPLACE INTO flags (username, flag) VALUES (?, ?)",
        (username, new_flag)
    )
    conn.commit()
    conn.close()


def get_leaderboard():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.username, p.current_stage, p.updated_at, f.flag,
               (SELECT COUNT(*) FROM attempts a WHERE a.username = p.username AND a.result = 'pass') as pass_count,
               (SELECT COUNT(*) FROM attempts a WHERE a.username = p.username AND a.result = 'fail') as fail_count
        FROM progress p
        LEFT JOIN flags f ON p.username = f.username
        ORDER BY p.current_stage DESC, p.updated_at ASC;
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def reset_student(username):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM progress WHERE username = ?", (username,))
    cursor.execute("DELETE FROM attempts WHERE username = ?", (username,))
    cursor.execute("DELETE FROM answers WHERE username = ?", (username,))
    cursor.execute("DELETE FROM flags WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    seed_student(username)
