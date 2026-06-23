"""
SQLite历史记录数据库

被 survey_filler/submitter.py 和 ui/tabs/history_tab.py 调用
存储和查询填写历史记录
"""
import sqlite3
import os
from typing import List, Optional, Dict, Any


class HistoryDB:
    """SQLite历史记录数据库"""

    DB_FILENAME = "history.db"

    def __init__(self):
        self._data_dir = self._get_data_dir()
        self._db_path = os.path.join(self._data_dir, self.DB_FILENAME)
        self._init_db()

    @staticmethod
    def _get_data_dir() -> str:
        appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
        path = os.path.join(appdata, "QQSurveyAssistant")
        os.makedirs(path, exist_ok=True)
        return path

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    url TEXT NOT NULL,
                    profile_name TEXT NOT NULL,
                    success INTEGER NOT NULL DEFAULT 0,
                    fields_filled INTEGER DEFAULT 0,
                    fields_total INTEGER DEFAULT 0,
                    screenshot_path TEXT DEFAULT '',
                    error_message TEXT DEFAULT '',
                    note TEXT DEFAULT '',
                    created_at TEXT DEFAULT (datetime('now','localtime'))
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_history_time
                ON history(created_at DESC)
            """)
            conn.commit()

    def add_record(self, timestamp: str, url: str, profile_name: str,
                   success: bool, fields_filled: int = 0, fields_total: int = 0,
                   screenshot_path: str = "", error_message: str = "",
                   note: str = "") -> int:
        """添加记录，返回ID"""
        with self._get_conn() as conn:
            cursor = conn.execute("""
                INSERT INTO history
                (timestamp, url, profile_name, success, fields_filled,
                 fields_total, screenshot_path, error_message, note)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (timestamp, url, profile_name, int(success),
                  fields_filled, fields_total, screenshot_path,
                  error_message, note))
            conn.commit()
            return cursor.lastrowid

    def get_records(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """获取历史记录（按时间倒序）"""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM history
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset)).fetchall()
            return [dict(row) for row in rows]

    def get_record(self, record_id: int) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM history WHERE id = ?", (record_id,)
            ).fetchone()
            return dict(row) if row else None

    def delete_record(self, record_id: int):
        with self._get_conn() as conn:
            conn.execute("DELETE FROM history WHERE id = ?", (record_id,))
            conn.commit()

    def clear_all(self):
        with self._get_conn() as conn:
            conn.execute("DELETE FROM history")
            conn.commit()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._get_conn() as conn:
            total = conn.execute(
                "SELECT COUNT(*) as c FROM history"
            ).fetchone()["c"]
            success = conn.execute(
                "SELECT COUNT(*) as c FROM history WHERE success=1"
            ).fetchone()["c"]
            filled = conn.execute(
                "SELECT COALESCE(SUM(fields_filled),0) as c FROM history"
            ).fetchone()["c"]
            return {
                "total": total,
                "success": success,
                "failed": total - success,
                "total_fields_filled": filled
            }
