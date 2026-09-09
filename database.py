import os
import random
import string
import hashlib

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

USE_POSTGRES = bool(DATABASE_URL)
DB_PATH = os.path.join(os.path.dirname(__file__), "ctf.db")


class DBWrapper:
    def __init__(self):
        self.is_pg = USE_POSTGRES
        if self.is_pg:
            import psycopg2
            import psycopg2.extras
            self.conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        else:
            import sqlite3
            self.conn = sqlite3.connect(DB_PATH)
            self.conn.row_factory = sqlite3.Row

    def cursor(self):
        return CursorWrapper(self.conn.cursor(), self.is_pg)

    def commit(self):
        self.conn.commit()

    def rollback(self):
        try:
            self.conn.rollback()
        except Exception:
            pass

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass


class CursorWrapper:
    def __init__(self, cursor, is_pg):
        self.cursor = cursor
        self.is_pg = is_pg

    def execute(self, query, params=None):
        sql = query
        if self.is_pg:
            sql = sql.replace("?", "%s")
            if "INTEGER PRIMARY KEY AUTOINCREMENT" in sql:
                sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
        if params is not None:
            return self.cursor.execute(sql, params)
        return self.cursor.execute(sql)

    def fetchone(self):
        row = self.cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def fetchall(self):
        rows = self.cursor.fetchall()
        return [dict(r) for r in rows]


def get_db():
    return DBWrapper()


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
    conn.commit()

    # Progress table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            username TEXT PRIMARY KEY,
            current_stage INTEGER DEFAULT 1,
            ctf1_stage INTEGER DEFAULT 1,
            ctf2_stage INTEGER DEFAULT 1,
            active_ctf INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()

    # Attempts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            stage INTEGER,
            ctf_id INTEGER DEFAULT 1,
            result TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()

    # Answers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS answers (
            username TEXT,
            stage INTEGER,
            expected TEXT,
            PRIMARY KEY (username, stage)
        );
    """)
    conn.commit()

    # Flags table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS flags (
            username TEXT PRIMARY KEY,
            flag TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()

    # Stage scores table (tracks 1 = clean pass, 0 = assisted pass / over 3 attempts)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stage_scores (
            username TEXT,
            ctf_id INTEGER DEFAULT 1,
            stage INTEGER,
            score INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (username, ctf_id, stage)
        );
    """)
    conn.commit()

    # Stage timings table (tracks started_at, finished_at, duration_seconds)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stage_timings (
            username TEXT,
            ctf_id INTEGER DEFAULT 1,
            stage INTEGER,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            finished_at TIMESTAMP,
            duration_seconds INTEGER DEFAULT 0,
            PRIMARY KEY (username, ctf_id, stage)
        );
    """)
    conn.commit()

    # Migration for existing tables
    if conn.is_pg:
        for q in [
            "ALTER TABLE progress ADD COLUMN IF NOT EXISTS ctf1_stage INTEGER DEFAULT 1;",
            "ALTER TABLE progress ADD COLUMN IF NOT EXISTS ctf2_stage INTEGER DEFAULT 1;",
            "ALTER TABLE progress ADD COLUMN IF NOT EXISTS active_ctf INTEGER DEFAULT 1;",
            "ALTER TABLE progress ADD COLUMN IF NOT EXISTS vfs_data TEXT;",
            "ALTER TABLE attempts ADD COLUMN IF NOT EXISTS ctf_id INTEGER DEFAULT 1;"
        ]:
            try:
                cursor.execute(q)
                conn.commit()
            except Exception:
                conn.rollback()
    else:
        for q in [
            "ALTER TABLE progress ADD COLUMN ctf1_stage INTEGER DEFAULT 1;",
            "ALTER TABLE progress ADD COLUMN ctf2_stage INTEGER DEFAULT 1;",
            "ALTER TABLE progress ADD COLUMN active_ctf INTEGER DEFAULT 1;",
            "ALTER TABLE progress ADD COLUMN vfs_data TEXT;",
            "ALTER TABLE attempts ADD COLUMN ctf_id INTEGER DEFAULT 1;"
        ]:
            try:
                cursor.execute(q)
                conn.commit()
            except Exception:
                pass

    # Migrate any existing current_stage data
    try:
        cursor.execute("""
            UPDATE progress
            SET ctf1_stage = CASE WHEN current_stage > 10 THEN 11 ELSE COALESCE(current_stage, 1) END,
                ctf2_stage = CASE WHEN current_stage > 10 THEN current_stage - 10 ELSE 1 END
            WHERE (ctf1_stage = 1 AND current_stage > 1) OR ctf1_stage IS NULL OR ctf1_stage = 0;
        """)
        conn.commit()
    except Exception:
        if conn.is_pg:
            conn.rollback()

    # Sync data from SQLite (ctf.db) to PostgreSQL if running with PostgreSQL
    if conn.is_pg and os.path.exists(DB_PATH):
        try:
            import sqlite3
            sq_conn = sqlite3.connect(DB_PATH)
            sq_conn.row_factory = sqlite3.Row
            sq_cur = sq_conn.cursor()

            # 1. users
            sq_cur.execute("SELECT username, password_hash, created_at FROM users")
            for u in sq_cur.fetchall():
                cursor.execute(
                    "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?) ON CONFLICT (username) DO NOTHING;",
                    (u["username"], u["password_hash"], u["created_at"])
                )

            # 2. progress
            sq_cur.execute("SELECT username, current_stage, ctf1_stage, ctf2_stage, active_ctf, created_at, updated_at FROM progress")
            for p in sq_cur.fetchall():
                c1 = p["ctf1_stage"] if p["ctf1_stage"] else (11 if p["current_stage"] > 10 else p["current_stage"])
                c2 = p["ctf2_stage"] if p["ctf2_stage"] else 1
                act = p["active_ctf"] if p["active_ctf"] else 1
                cursor.execute("""
                    INSERT INTO progress (username, current_stage, ctf1_stage, ctf2_stage, active_ctf, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (username) DO UPDATE 
                    SET ctf1_stage = CASE WHEN progress.ctf1_stage < EXCLUDED.ctf1_stage THEN EXCLUDED.ctf1_stage ELSE progress.ctf1_stage END,
                        current_stage = CASE WHEN progress.current_stage < EXCLUDED.current_stage THEN EXCLUDED.current_stage ELSE progress.current_stage END;
                """, (p["username"], p["current_stage"], c1, c2, act, p["created_at"], p["updated_at"]))

            # 3. answers
            sq_cur.execute("SELECT username, stage, expected FROM answers")
            for a in sq_cur.fetchall():
                cursor.execute(
                    "INSERT INTO answers (username, stage, expected) VALUES (?, ?, ?) ON CONFLICT (username, stage) DO NOTHING;",
                    (a["username"], a["stage"], a["expected"])
                )

            # 4. flags
            sq_cur.execute("SELECT username, flag, created_at FROM flags")
            for f in sq_cur.fetchall():
                cursor.execute(
                    "INSERT INTO flags (username, flag, created_at) VALUES (?, ?, ?) ON CONFLICT (username) DO UPDATE SET flag = EXCLUDED.flag;",
                    (f["username"], f["flag"], f["created_at"])
                )

            conn.commit()
            sq_conn.close()
        except Exception:
            if conn.is_pg:
                conn.rollback()

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

    cursor.execute("SELECT username FROM progress WHERE username = ?", (username,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO progress (username, current_stage, ctf1_stage, ctf2_stage, active_ctf) VALUES (?, 1, 1, 1, 1)", (username,))

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

    # Quiz 13 (Line number of isolated word)
    cursor.execute("SELECT expected FROM answers WHERE username = ? AND stage = 13", (username,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO answers (username, stage, expected) VALUES (?, 13, ?)", (username, "23"))

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


def get_student_ctf_status(username):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT current_stage, ctf1_stage, ctf2_stage, active_ctf FROM progress WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return {"active_ctf": 1, "ctf1_stage": 1, "ctf2_stage": 1, "ctf2_unlocked": False}
    
    ctf1 = row.get("ctf1_stage") or row.get("current_stage") or 1
    ctf2 = row.get("ctf2_stage") or 1
    active = row.get("active_ctf") or 1
    unlocked = (ctf1 > 10)
    return {
        "active_ctf": active,
        "ctf1_stage": ctf1,
        "ctf2_stage": ctf2,
        "ctf2_unlocked": unlocked
    }


def switch_active_ctf(username, target_ctf):
    target_ctf = int(target_ctf)
    if target_ctf not in (1, 2):
        return {"ok": False, "error": "Noto'g'ri CTF tanlandi."}
    status = get_student_ctf_status(username)
    if target_ctf == 2 and not status["ctf2_unlocked"]:
        return {
            "ok": False,
            "error": "🔒 CTF 2 hali qulflangan! Undan foydalanish uchun avval CTF 1 ning barcha 10 ta bosqichini yakunlab, 1-Flagni qo'lga kiritishingiz kerak."
        }
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE progress SET active_ctf = ?, updated_at = CURRENT_TIMESTAMP WHERE username = ?", (target_ctf, username))
    conn.commit()
    conn.close()
    return {"ok": True, "active_ctf": target_ctf}


def get_student_stage(username):
    status = get_student_ctf_status(username)
    if status["active_ctf"] == 2:
        return status["ctf2_stage"]
    return status["ctf1_stage"]


def get_student_answers(username):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT stage, expected FROM answers WHERE username = ?", (username,))
    rows = cursor.fetchall()
    conn.close()
    return {row["stage"]: row["expected"] for row in rows}


def log_attempt(username, stage, result, ctf=None):
    if ctf is None:
        ctf = get_student_ctf_status(username)["active_ctf"]
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO attempts (username, stage, result, ctf_id) VALUES (?, ?, ?, ?)",
        (username, stage, result, ctf)
    )
    conn.commit()
    conn.close()


def get_stage_fail_count(username, stage, ctf=None):
    if ctf is None:
        ctf = get_student_ctf_status(username)["active_ctf"]
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) as cnt FROM attempts WHERE username = ? AND stage = ? AND ctf_id = ? AND result = 'fail'",
        (username, stage, ctf)
    )
    row = cursor.fetchone()
    conn.close()
    return row["cnt"] if row else 0


def update_student_stage(username, next_stage):
    status = get_student_ctf_status(username)
    conn = get_db()
    cursor = conn.cursor()
    if status["active_ctf"] == 2:
        cursor.execute(
            "UPDATE progress SET ctf2_stage = ?, updated_at = CURRENT_TIMESTAMP WHERE username = ?",
            (next_stage, username)
        )
    else:
        cursor.execute(
            "UPDATE progress SET ctf1_stage = ?, updated_at = CURRENT_TIMESTAMP WHERE username = ?",
            (next_stage, username)
        )
    conn.commit()
    conn.close()
def record_stage_score(username, ctf_id, stage, score):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO stage_scores (username, ctf_id, stage, score) 
        VALUES (?, ?, ?, ?)
        ON CONFLICT (username, ctf_id, stage) DO UPDATE SET score = EXCLUDED.score;
    """, (username, ctf_id, stage, score))
    conn.commit()
    conn.close()


def record_stage_start(username, ctf_id, stage):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO stage_timings (username, ctf_id, stage, started_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT (username, ctf_id, stage) DO NOTHING;
        """, (username, ctf_id, stage))
        conn.commit()
        conn.close()
    except Exception:
        pass


def record_stage_finish(username, ctf_id, stage):
    try:
        conn = get_db()
        cursor = conn.cursor()
        # Find started_at
        cursor.execute("SELECT started_at FROM stage_timings WHERE username = ? AND ctf_id = ? AND stage = ?", (username, ctf_id, stage))
        row = cursor.fetchone()
        duration = 0
        if row and row.get("started_at"):
            import datetime
            try:
                start_dt = datetime.datetime.fromisoformat(str(row["started_at"]).replace("Z", ""))
                duration = max(1, int((datetime.datetime.utcnow() - start_dt).total_seconds()))
            except Exception:
                duration = 60
        else:
            duration = 60

        cursor.execute("""
            INSERT INTO stage_timings (username, ctf_id, stage, finished_at, duration_seconds)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?)
            ON CONFLICT (username, ctf_id, stage) DO UPDATE
            SET finished_at = CURRENT_TIMESTAMP, duration_seconds = EXCLUDED.duration_seconds;
        """, (username, ctf_id, stage, duration))
        conn.commit()
        conn.close()
    except Exception:
        pass


def get_total_clean_score(username):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COALESCE(SUM(score), 0) as total FROM stage_scores WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return row["total"] if row else 0

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

    cursor.execute("DELETE FROM flags WHERE username = ?", (username,))
    cursor.execute(
        "INSERT INTO flags (username, flag) VALUES (?, ?)",
        (username, new_flag)
    )
    conn.commit()
    conn.close()


def get_leaderboard():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.username, 
               COALESCE(p.ctf1_stage, p.current_stage, 1) as ctf1_stage,
               COALESCE(p.ctf2_stage, 1) as ctf2_stage,
               COALESCE(p.active_ctf, 1) as active_ctf,
               (CASE WHEN COALESCE(p.active_ctf, 1) = 2 THEN COALESCE(p.ctf2_stage, 1) ELSE COALESCE(p.ctf1_stage, 1) END) as current_stage,
               p.updated_at, f.flag,
               COALESCE((SELECT SUM(score) FROM stage_scores s WHERE s.username = p.username), 
                        ((CASE WHEN COALESCE(p.ctf1_stage, 1) > 10 THEN 10 ELSE COALESCE(p.ctf1_stage, 1) - 1 END) +
                         (CASE WHEN COALESCE(p.ctf2_stage, 1) > 10 THEN 10 ELSE COALESCE(p.ctf2_stage, 1) - 1 END))) as pass_count,
               (SELECT COUNT(*) FROM attempts a WHERE a.username = p.username AND a.result = 'fail') as fail_count
        FROM progress p
        LEFT JOIN flags f ON p.username = f.username
        ORDER BY 
            pass_count DESC,
            (COALESCE(p.ctf1_stage, 1) + COALESCE(p.ctf2_stage, 1)) DESC,
            p.updated_at ASC;
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
    cursor.execute("DELETE FROM stage_scores WHERE username = ?", (username,))
    cursor.execute("DELETE FROM stage_timings WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    seed_student(username)


def save_user_vfs(username, fs):
    try:
        import json
        data_str = json.dumps(fs)
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE progress SET vfs_data = ? WHERE username = ?", (data_str, username))
        conn.commit()
        conn.close()
    except Exception:
        pass


def load_user_vfs(username):
    try:
        import json
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT vfs_data FROM progress WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        if row and row.get("vfs_data"):
            return json.loads(row["vfs_data"])
    except Exception:
        pass
    return None


# ── Admin Diagnostics & Telemetry ──────────────────────────────

def get_admin_overview():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total_users FROM users")
    u_row = cursor.fetchone()
    total_users = u_row["total_users"] if u_row else 0

    cursor.execute("SELECT COUNT(*) as ctf1_finished FROM progress WHERE ctf1_stage > 10")
    c1_row = cursor.fetchone()
    ctf1_finished = c1_row["ctf1_finished"] if c1_row else 0

    cursor.execute("SELECT COUNT(*) as ctf2_finished FROM progress WHERE ctf2_stage > 10")
    c2_row = cursor.fetchone()
    ctf2_finished = c2_row["ctf2_finished"] if c2_row else 0

    cursor.execute("SELECT COUNT(*) as total_attempts FROM attempts")
    att_row = cursor.fetchone()
    total_attempts = att_row["total_attempts"] if att_row else 0

    cursor.execute("SELECT COUNT(*) as total_fails FROM attempts WHERE result = 'fail'")
    fail_row = cursor.fetchone()
    total_fails = fail_row["total_fails"] if fail_row else 0

    cursor.execute("SELECT COALESCE(SUM(duration_seconds), 0) as total_duration FROM stage_timings")
    dur_row = cursor.fetchone()
    total_duration_sec = dur_row["total_duration"] if dur_row else 0
    total_hours = round(total_duration_sec / 3600, 1)

    conn.close()
    return {
        "total_users": total_users,
        "ctf1_finished": ctf1_finished,
        "ctf2_finished": ctf2_finished,
        "total_attempts": total_attempts,
        "total_fails": total_fails,
        "total_hours": total_hours
    }


def get_admin_users():
    """Returns all users with extended stats for admin panel table."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.username, u.created_at as registered_at,
               COALESCE(p.ctf1_stage, 1) as ctf1_stage,
               COALESCE(p.ctf2_stage, 1) as ctf2_stage,
               COALESCE(p.active_ctf, 1) as active_ctf,
               p.updated_at,
               f.flag,
               COALESCE((SELECT SUM(score) FROM stage_scores s WHERE s.username = u.username), 0) as total_score,
               (SELECT COUNT(*) FROM attempts a WHERE a.username = u.username AND a.result = 'fail') as total_fails,
               COALESCE((SELECT SUM(duration_seconds) FROM stage_timings t WHERE t.username = u.username), 0) as total_duration_sec
        FROM users u
        LEFT JOIN progress p ON u.username = p.username
        LEFT JOIN flags f ON u.username = f.username
        ORDER BY total_score DESC, total_fails ASC, registered_at DESC;
    """)
    rows = cursor.fetchall()
    conn.close()

    result = []
    for r in rows:
        d = dict(r)
        dur = d.get("total_duration_sec", 0)
        d["total_time_str"] = f"{dur//3600}h {(dur%3600)//60}m" if dur >= 3600 else f"{dur//60}m {dur%60}s" if dur > 0 else "0s"
        d["ctf1_completed"] = d.get("ctf1_stage", 1) > 10
        d["ctf2_completed"] = d.get("ctf2_stage", 1) > 10
        result.append(d)
    return result


def get_student_audit_detail(username, quiz_meta_1=None, quiz_meta_2=None):
    """Deep inspection of a single student: fails per stage, where failed, duration per stage, scores."""
    conn = get_db()
    cursor = conn.cursor()

    # User basic info
    cursor.execute("SELECT username, current_stage, ctf1_stage, ctf2_stage, active_ctf, created_at, updated_at FROM progress WHERE username = ?", (username,))
    p = cursor.fetchone()
    if not p:
        conn.close()
        return None

    prog = dict(p)

    # All attempts grouped by (ctf_id, stage)
    cursor.execute("""
        SELECT ctf_id, stage, result, created_at
        FROM attempts
        WHERE username = ?
        ORDER BY id ASC
    """, (username,))
    raw_attempts = cursor.fetchall()

    # Scores
    cursor.execute("SELECT ctf_id, stage, score FROM stage_scores WHERE username = ?", (username,))
    score_map = {(r["ctf_id"], r["stage"]): r["score"] for r in cursor.fetchall()}

    # Timings
    cursor.execute("SELECT ctf_id, stage, started_at, finished_at, duration_seconds FROM stage_timings WHERE username = ?", (username,))
    timing_map = {(r["ctf_id"], r["stage"]): dict(r) for r in cursor.fetchall()}

    # Group attempts by stage
    attempts_map = {}
    for a in raw_attempts:
        key = (a.get("ctf_id", 1), a["stage"])
        if key not in attempts_map:
            attempts_map[key] = {"fails": 0, "passes": 0, "logs": []}
        if a["result"] == "fail":
            attempts_map[key]["fails"] += 1
        else:
            attempts_map[key]["passes"] += 1
        attempts_map[key]["logs"].append({
            "result": a["result"],
            "time": str(a["created_at"])
        })

    import datetime

    # Build 20 stage breakdown
    stages_audit = []

    # CTF 1 stages (1-10)
    for s in range(1, 11):
        key = (1, s)
        att = attempts_map.get(key, {"fails": 0, "passes": 0, "logs": []})
        tm = timing_map.get(key, {})
        score = score_map.get(key, 1 if att["passes"] > 0 and att["fails"] <= 3 else 0)
        dur = tm.get("duration_seconds", 0)

        is_completed = (prog.get("ctf1_stage") or 1) > s
        is_current = (prog.get("ctf1_stage") or 1) == s and prog.get("active_ctf", 1) == 1

        # Live duration calculation if currently active
        dur_str = "—"
        if is_completed:
            dur_str = f"{dur//60}m {dur%60}s" if dur >= 60 else f"{dur}s" if dur > 0 else "45s"
        elif is_current:
            if tm.get("started_at"):
                try:
                    start_dt = datetime.datetime.fromisoformat(str(tm["started_at"]).replace("Z", ""))
                    live_dur = max(1, int((datetime.datetime.utcnow() - start_dt).total_seconds()))
                    dur_str = f"⏳ {live_dur//60}m {live_dur%60}s (ishlanmoqda)"
                    dur = live_dur
                except Exception:
                    dur_str = "⏳ Jarayonda"
            else:
                dur_str = "⏳ Jarayonda"

        # Where did they fail / status description
        meta = (quiz_meta_1 or {}).get(s, {})
        quiz_title = meta.get("title", f"Quiz {s}")
        quiz_cmd = meta.get("commands", "")
        quiz_desc = meta.get("description", "")

        status_badge = "🔒 Qulflangan"
        status_code = "locked"
        if is_completed:
            status_code = "completed"
            if att["fails"] == 0:
                status_badge = "🟢 Silliq (0 xato)"
            elif att["fails"] <= 3:
                status_badge = f"🟡 {att['fails']} ta xato (Mustaqil)"
            else:
                status_badge = f"🔴 {att['fails']} ta xato (Maslahat bilan)"
        elif is_current:
            status_code = "current"
            status_badge = f"⚡ Hozir ishlanmoqda ({att['fails']} ta xato)"

        stages_audit.append({
            "ctf_id": 1,
            "stage": s,
            "name": f"CTF 1: {quiz_title}",
            "commands": quiz_cmd,
            "description": quiz_desc,
            "completed": is_completed,
            "current": is_current,
            "status_code": status_code,
            "status_badge": status_badge,
            "fails": att["fails"],
            "score": score if is_completed else 0,
            "duration_str": dur_str,
            "duration_seconds": dur,
            "attempts_count": len(att["logs"])
        })

    # CTF 2 stages (1-10)
    for s in range(1, 11):
        key = (2, s)
        att = attempts_map.get(key, {"fails": 0, "passes": 0, "logs": []})
        tm = timing_map.get(key, {})
        score = score_map.get(key, 1 if att["passes"] > 0 and att["fails"] <= 3 else 0)
        dur = tm.get("duration_seconds", 0)

        is_completed = (prog.get("ctf2_stage") or 1) > s
        is_current = (prog.get("ctf2_stage") or 1) == s and prog.get("active_ctf", 1) == 2

        dur_str = "—"
        if is_completed:
            dur_str = f"{dur//60}m {dur%60}s" if dur >= 60 else f"{dur}s" if dur > 0 else "50s"
        elif is_current:
            if tm.get("started_at"):
                try:
                    start_dt = datetime.datetime.fromisoformat(str(tm["started_at"]).replace("Z", ""))
                    live_dur = max(1, int((datetime.datetime.utcnow() - start_dt).total_seconds()))
                    dur_str = f"⏳ {live_dur//60}m {live_dur%60}s (ishlanmoqda)"
                    dur = live_dur
                except Exception:
                    dur_str = "⏳ Jarayonda"
            else:
                dur_str = "⏳ Jarayonda"

        meta = (quiz_meta_2 or {}).get(s, {})
        quiz_title = meta.get("title", f"Quiz {s}")
        quiz_cmd = meta.get("commands", "")
        quiz_desc = meta.get("description", "")

        status_badge = "🔒 Qulflangan"
        status_code = "locked"
        if is_completed:
            status_code = "completed"
            if att["fails"] == 0:
                status_badge = "🟢 Silliq (0 xato)"
            elif att["fails"] <= 3:
                status_badge = f"🟡 {att['fails']} ta xato (Mustaqil)"
            else:
                status_badge = f"🔴 {att['fails']} ta xato (Maslahat bilan)"
        elif is_current:
            status_code = "current"
            status_badge = f"⚡ Hozir ishlanmoqda ({att['fails']} ta xato)"

        stages_audit.append({
            "ctf_id": 2,
            "stage": s,
            "name": f"CTF 2: {quiz_title}",
            "commands": quiz_cmd,
            "description": quiz_desc,
            "completed": is_completed,
            "current": is_current,
            "status_code": status_code,
            "status_badge": status_badge,
            "fails": att["fails"],
            "score": score if is_completed else 0,
            "duration_str": dur_str,
            "duration_seconds": dur,
            "attempts_count": len(att["logs"])
        })

    # Flags
    cursor.execute("SELECT flag FROM flags WHERE username = ?", (username,))
    flag_row = cursor.fetchone()
    flags_val = flag_row["flag"] if flag_row else ""

    conn.close()

    total_time_sec = sum(st["duration_seconds"] for st in stages_audit)
    total_time_str = f"{total_time_sec//3600}h {(total_time_sec%3600)//60}m {total_time_sec%60}s" if total_time_sec >= 3600 else f"{total_time_sec//60}m {total_time_sec%60}s"

    return {
        "username": username,
        "progress": prog,
        "flag": flags_val,
        "total_score": sum(st["score"] for st in stages_audit),
        "total_fails": sum(st["fails"] for st in stages_audit),
        "total_time_str": total_time_str,
        "stages": stages_audit
    }
