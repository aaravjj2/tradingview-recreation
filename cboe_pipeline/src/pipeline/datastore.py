import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

class DataStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
        self.lock = threading.Lock()

    def _init_db(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    month TEXT,
                    symbol TEXT,
                    status TEXT,
                    file_path TEXT,
                    size INTEGER,
                    checksum TEXT,
                    attempts INTEGER DEFAULT 0,
                    last_error TEXT,
                    updated_at TIMESTAMP,
                    PRIMARY KEY (month, symbol)
                )
            """)
            conn.commit()

    def get_task(self, month: str, symbol: str) -> Optional[dict]:
        with self.lock, sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute("SELECT * FROM tasks WHERE month = ? AND symbol = ?", (month, symbol))
            row = cur.fetchone()
            return dict(row) if row else None

    def update_task(self, month: str, symbol: str, status: str, **kwargs):
        with self.lock, sqlite3.connect(self.db_path) as conn:
            cols = ["status", "updated_at"]
            vals = [status, datetime.utcnow()]
            
            for k, v in kwargs.items():
                cols.append(k)
                vals.append(v)
            
            set_clause = ", ".join([f"{c} = ?" for c in cols])
            # Check existence
            cur = conn.execute("SELECT 1 FROM tasks WHERE month = ? AND symbol = ?", (month, symbol))
            if cur.fetchone():
                conn.execute(f"UPDATE tasks SET {set_clause} WHERE month = ? AND symbol = ?", (*vals, month, symbol))
            else:
                cols.extend(["month", "symbol"])
                vals.extend([month, symbol])
                placeholders = ", ".join(["?" for _ in vals])
                conn.execute(f"INSERT INTO tasks ({', '.join(cols)}) VALUES ({placeholders})", vals)
            conn.commit()

    def get_pending_downloads(self) -> List[Tuple[str, str]]:
        with self.lock, sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT month, symbol FROM tasks WHERE status NOT IN ('DOWNLOADED', 'PROCESSED') ORDER BY month, symbol")
            return [(row[0], row[1]) for row in cur.fetchall()]
