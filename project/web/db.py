#!/usr/bin/env python3
"""SQLite 数据层：用户、会话、审核事件、入库台账、待人审队列。

业务关系（人话）：
  用户 ——审——> 日志 ——产生——> 审核事件
  用户 ——定稿——> 入库记录（一份日志对应一条正式结果）
  用户 ——批量排队——> 待人审条目 ——打开——> 工作台继续审
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
DB_PATH = DATA_DIR / "product_requirement.db"

_lock = threading.RLock()
_local = threading.local()


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")


def _now_iso_expire(hours: int = 24 * 7) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).astimezone().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def ensure_db() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with _lock:
        conn = sqlite3.connect(str(DB_PATH))
        try:
            conn.executescript(SCHEMA)
            conn.commit()
            _seed_demo_user(conn)
            conn.commit()
        finally:
            conn.close()
    return DB_PATH


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE COLLATE NOCASE,
  display_name TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'reviewer',
  created_at TEXT NOT NULL,
  last_login_at TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
  token TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
  id TEXT PRIMARY KEY,
  at TEXT NOT NULL,
  user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  actor_name TEXT NOT NULL,
  journal_id TEXT,
  journal_title TEXT,
  journal_fingerprint TEXT,
  step TEXT NOT NULL,
  action TEXT NOT NULL,
  code TEXT,
  reason TEXT,
  summary TEXT NOT NULL,
  artifact_json TEXT,
  phase_after TEXT
);
CREATE INDEX IF NOT EXISTS idx_audit_journal ON audit_events(journal_id, at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_events(user_id, at DESC);

CREATE TABLE IF NOT EXISTS approved_records (
  journal_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  product TEXT,
  fingerprint TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'approved',
  approver_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  approver_name TEXT NOT NULL,
  approved_at TEXT NOT NULL,
  accepted_path TEXT,
  story_count INTEGER NOT NULL DEFAULT 0,
  accepted_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_approved_at ON approved_records(approved_at DESC);
CREATE INDEX IF NOT EXISTS idx_approved_approver ON approved_records(approver_name);

CREATE TABLE IF NOT EXISTS review_queue (
  id TEXT PRIMARY KEY,
  journal_id TEXT NOT NULL,
  journal_title TEXT,
  product TEXT,
  status TEXT NOT NULL,
  actor_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  actor_name TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  error TEXT,
  artifact_dir TEXT,
  story_chars INTEGER DEFAULT 0,
  story_count INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_queue_status ON review_queue(status, updated_at DESC);

CREATE TABLE IF NOT EXISTS schema_meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
"""


def connect() -> sqlite3.Connection:
    ensure_db()
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_conn() -> sqlite3.Connection:
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = connect()
        _local.conn = conn
    return conn


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


def _seed_demo_user(conn: sqlite3.Connection) -> None:
    from auth_passwords import hash_password  # local

    cur = conn.execute("SELECT id FROM users WHERE username = ?", ("demo",))
    if cur.fetchone():
        return
    conn.execute(
        """
        INSERT INTO users(username, display_name, password_hash, role, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("demo", "演示账号", hash_password("demo1234"), "admin", _now()),
    )
    conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('seed_demo', '1')"
    )


def migrate_json_registry_once() -> None:
    """把旧 JSON 台账迁进 SQLite（只跑一次）。"""
    ensure_db()
    reg_path = DATA_DIR / "approved_registry.json"
    conn = connect()
    try:
        done = conn.execute(
            "SELECT value FROM schema_meta WHERE key = 'migrated_registry'"
        ).fetchone()
        if done:
            return
        if reg_path.exists():
            data = json.loads(reg_path.read_text(encoding="utf-8"))
            items = data.get("items") or {}
            for jid, rec in items.items():
                conn.execute(
                    """
                    INSERT INTO approved_records(
                      journal_id, title, product, fingerprint, status,
                      approver_user_id, approver_name, approved_at, accepted_path, story_count
                    ) VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?, ?)
                    ON CONFLICT(journal_id) DO NOTHING
                    """,
                    (
                        jid,
                        rec.get("title") or jid,
                        rec.get("product"),
                        rec.get("fingerprint") or "",
                        rec.get("status") or "approved",
                        rec.get("approver") or "",
                        rec.get("approved_at") or _now(),
                        rec.get("accepted_path"),
                        int(rec.get("story_count") or 0),
                    ),
                )
        conn.execute(
            "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('migrated_registry', '1')"
        )
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


# ---------- users / sessions ----------


def create_user(username: str, password: str, display_name: str = "") -> dict:
    from auth_passwords import hash_password

    name = (username or "").strip()
    pwd = password or ""
    if len(name) < 2:
        raise ValueError("用户名至少 2 个字")
    if len(pwd) < 6:
        raise ValueError("密码至少 6 位")
    disp = (display_name or "").strip() or name
    with _lock:
        conn = connect()
        try:
            conn.execute(
                """
                INSERT INTO users(username, display_name, password_hash, role, created_at)
                VALUES (?, ?, ?, 'reviewer', ?)
                """,
                (name, disp, hash_password(pwd), _now()),
            )
            conn.commit()
            row = conn.execute(
                "SELECT id, username, display_name, role, created_at FROM users WHERE username = ?",
                (name,),
            ).fetchone()
            return row_to_dict(row)  # type: ignore
        except sqlite3.IntegrityError as e:
            raise ValueError("用户名已被注册") from e
        finally:
            conn.close()


def verify_login(username: str, password: str) -> dict:
    from auth_passwords import verify_password

    name = (username or "").strip()
    conn = connect()
    try:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (name,)).fetchone()
        if not row or not verify_password(password or "", row["password_hash"]):
            raise ValueError("用户名或密码不对")
        conn.execute(
            "UPDATE users SET last_login_at = ? WHERE id = ?", (_now(), row["id"])
        )
        conn.commit()
        return {
            "id": row["id"],
            "username": row["username"],
            "display_name": row["display_name"],
            "role": row["role"],
        }
    finally:
        conn.close()


def create_session(user_id: int) -> str:
    token = uuid.uuid4().hex + uuid.uuid4().hex
    conn = connect()
    try:
        conn.execute(
            "INSERT INTO sessions(token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token, user_id, _now(), _now_iso_expire()),
        )
        conn.commit()
        return token
    finally:
        conn.close()


def get_user_by_token(token: str | None) -> dict | None:
    if not token:
        return None
    conn = connect()
    try:
        row = conn.execute(
            """
            SELECT u.id, u.username, u.display_name, u.role, s.expires_at
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token = ?
            """,
            (token,),
        ).fetchone()
        if not row:
            return None
        if (row["expires_at"] or "") < _now():
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
            return None
        return {
            "id": row["id"],
            "username": row["username"],
            "display_name": row["display_name"],
            "role": row["role"],
        }
    finally:
        conn.close()


def delete_session(token: str | None) -> None:
    if not token:
        return
    conn = connect()
    try:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
    finally:
        conn.close()


# ---------- audit ----------


def db_append_event(event: dict) -> dict:
    conn = connect()
    try:
        at = event.get("at") or _now()
        eid = event.get("id") or f"evt_{uuid.uuid4().hex[:12]}"
        conn.execute(
            """
            INSERT INTO audit_events(
              id, at, user_id, actor_name, journal_id, journal_title, journal_fingerprint,
              step, action, code, reason, summary, artifact_json, phase_after
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                eid,
                at,
                event.get("user_id"),
                event.get("actor") or event.get("actor_name") or "未署名",
                event.get("journal_id"),
                event.get("journal_title"),
                event.get("journal_fingerprint"),
                event.get("step"),
                event.get("action"),
                event.get("code"),
                event.get("reason"),
                event.get("summary"),
                json.dumps(event.get("artifact") or {}, ensure_ascii=False),
                event.get("phase_after"),
            ),
        )
        conn.commit()
        event["id"] = eid
        event["at"] = at
        return event
    finally:
        conn.close()


def db_list_events(journal_id: str | None = None, limit: int = 200) -> list[dict]:
    conn = connect()
    try:
        if journal_id:
            rows = conn.execute(
                """
                SELECT * FROM audit_events
                WHERE journal_id = ?
                ORDER BY at DESC, id DESC
                LIMIT ?
                """,
                (journal_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM audit_events
                ORDER BY at DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        out = []
        for r in rows:
            d = row_to_dict(r) or {}
            try:
                d["artifact"] = json.loads(d.pop("artifact_json") or "{}")
            except Exception:
                d["artifact"] = {}
            d["actor"] = d.pop("actor_name", None)
            out.append(d)
        return out
    finally:
        conn.close()


# ---------- approved ----------


def db_register_approved(rec: dict) -> dict:
    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO approved_records(
              journal_id, title, product, fingerprint, status,
              approver_user_id, approver_name, approved_at, accepted_path, story_count, accepted_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(journal_id) DO UPDATE SET
              title=excluded.title,
              product=excluded.product,
              fingerprint=excluded.fingerprint,
              status=excluded.status,
              approver_user_id=excluded.approver_user_id,
              approver_name=excluded.approver_name,
              approved_at=excluded.approved_at,
              accepted_path=excluded.accepted_path,
              story_count=excluded.story_count,
              accepted_json=excluded.accepted_json
            """,
            (
                rec["journal_id"],
                rec.get("title") or rec["journal_id"],
                rec.get("product"),
                rec.get("fingerprint") or "",
                rec.get("status") or "approved",
                rec.get("approver_user_id"),
                rec.get("approver") or rec.get("approver_name") or "",
                rec.get("approved_at") or _now(),
                rec.get("accepted_path"),
                int(rec.get("story_count") or 0),
                rec.get("accepted_json"),
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM approved_records WHERE journal_id = ?", (rec["journal_id"],)
        ).fetchone()
        d = row_to_dict(row) or {}
        d["approver"] = d.get("approver_name")
        return d
    finally:
        conn.close()


def db_get_approved(journal_id: str) -> dict | None:
    conn = connect()
    try:
        row = conn.execute(
            "SELECT * FROM approved_records WHERE journal_id = ?", (journal_id,)
        ).fetchone()
        d = row_to_dict(row)
        if d:
            d["approver"] = d.get("approver_name")
        return d
    finally:
        conn.close()


def db_list_approved(q: str = "") -> list[dict]:
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT * FROM approved_records ORDER BY approved_at DESC"
        ).fetchall()
        items = []
        qq = (q or "").strip().lower()
        for r in rows:
            d = row_to_dict(r) or {}
            d["approver"] = d.get("approver_name")
            if qq:
                blob = " ".join(
                    str(d.get(k) or "")
                    for k in ("journal_id", "title", "approver_name", "product", "status")
                ).lower()
                if qq not in blob:
                    continue
            items.append(d)
        return items
    finally:
        conn.close()


def db_approved_map() -> dict[str, dict]:
    return {x["journal_id"]: x for x in db_list_approved()}


# ---------- queue ----------


def db_queue_upsert(item: dict) -> dict:
    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO review_queue(
              id, journal_id, journal_title, product, status, actor_user_id, actor_name,
              created_at, updated_at, error, artifact_dir, story_chars, story_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              status=excluded.status,
              updated_at=excluded.updated_at,
              error=excluded.error,
              story_chars=excluded.story_chars,
              story_count=excluded.story_count,
              journal_title=excluded.journal_title
            """,
            (
                item["id"],
                item["journal_id"],
                item.get("journal_title"),
                item.get("product"),
                item["status"],
                item.get("actor_user_id"),
                item.get("actor"),
                item.get("created_at") or _now(),
                item.get("updated_at") or _now(),
                item.get("error"),
                item.get("artifact_dir"),
                int(item.get("story_chars") or 0),
                int(item.get("story_count") or 0),
            ),
        )
        conn.commit()
        return item
    finally:
        conn.close()


def db_queue_list(status: str | None = None) -> list[dict]:
    conn = connect()
    try:
        if status:
            rows = conn.execute(
                "SELECT * FROM review_queue WHERE status = ? ORDER BY updated_at DESC",
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM review_queue ORDER BY updated_at DESC"
            ).fetchall()
        out = []
        for r in rows:
            d = row_to_dict(r) or {}
            d["actor"] = d.get("actor_name")
            out.append(d)
        return out
    finally:
        conn.close()


def db_queue_get(item_id: str) -> dict | None:
    conn = connect()
    try:
        row = conn.execute(
            "SELECT * FROM review_queue WHERE id = ?", (item_id,)
        ).fetchone()
        d = row_to_dict(row)
        if d:
            d["actor"] = d.get("actor_name")
        return d
    finally:
        conn.close()


def db_stats() -> dict:
    conn = connect()
    try:
        users = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
        audits = conn.execute("SELECT COUNT(*) AS n FROM audit_events").fetchone()["n"]
        approved = conn.execute("SELECT COUNT(*) AS n FROM approved_records").fetchone()["n"]
        pending = conn.execute(
            "SELECT COUNT(*) AS n FROM review_queue WHERE status = 'pending_human'"
        ).fetchone()["n"]
        return {
            "db_path": str(DB_PATH.relative_to(PROJECT_DIR)).replace("\\", "/"),
            "users": users,
            "audit_events": audits,
            "approved": approved,
            "pending_human": pending,
        }
    finally:
        conn.close()
