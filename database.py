import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional

class Database:
    def __init__(self, db_path: str = "sartaroshxona.db"):
        self.db_path = db_path
        self.init_db()

    def get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id     INTEGER PRIMARY KEY,
                    name        TEXT,
                    username    TEXT,
                    phone       TEXT,
                    created_at  TEXT DEFAULT (datetime('now')),
                    last_reminded TEXT
                );
                CREATE TABLE IF NOT EXISTS bookings (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id    INTEGER,
                    phone      TEXT,
                    date       TEXT,
                    time       TEXT,
                    service    TEXT,
                    status     TEXT DEFAULT 'pending',
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );
            """)

    def add_user(self, user_id, name, username):
        with self.get_conn() as conn:
            conn.execute("INSERT OR IGNORE INTO users (user_id, name, username) VALUES (?, ?, ?)", (user_id, name, username))

    def update_phone(self, user_id, phone):
        with self.get_conn() as conn:
            conn.execute("UPDATE users SET phone = ? WHERE user_id = ?", (phone, user_id))

    def get_users_for_reminder(self):
        threshold = (datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d %H:%M:%S")
        with self.get_conn() as conn:
            rows = conn.execute("SELECT user_id FROM users WHERE last_reminded IS NULL OR last_reminded < ?", (threshold,)).fetchall()
        return [dict(r) for r in rows]

    def update_reminder_sent(self, user_id):
        with self.get_conn() as conn:
            conn.execute("UPDATE users SET last_reminded = datetime('now') WHERE user_id = ?", (user_id,))

    def add_booking(self, user_id, phone, date, time, service):
        with self.get_conn() as conn:
            cur = conn.execute("INSERT INTO bookings (user_id, phone, date, time, service) VALUES (?, ?, ?, ?, ?)", (user_id, phone, date, time, service))
            return cur.lastrowid

    def get_booking(self, booking_id):
        with self.get_conn() as conn:
            row = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
        return dict(row) if row else None

    def update_booking_status(self, booking_id, status):
        with self.get_conn() as conn:
            conn.execute("UPDATE bookings SET status = ? WHERE id = ?", (status, booking_id))

    def get_booked_times(self, date):
        with self.get_conn() as conn:
            rows = conn.execute("SELECT time FROM bookings WHERE date = ?
