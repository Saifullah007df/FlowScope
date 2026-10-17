"""Local report history. Source text is never stored."""
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4

class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.execute('CREATE TABLE IF NOT EXISTS reports (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, project TEXT NOT NULL, title TEXT NOT NULL, kind TEXT NOT NULL, score REAL NOT NULL, report TEXT NOT NULL)')
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection
    def save(self, report, title, project):
        record = dict(report, id=uuid4().hex, title=title, project=project, created_at=datetime.now(timezone.utc).isoformat())
        with self.connect() as connection:
            connection.execute('INSERT INTO reports VALUES (?,?,?,?,?,?,?)', (record['id'], record['created_at'],project,title,record['kind'],record['quality']['value'],json.dumps(record,ensure_ascii=False)))
            connection.execute('DELETE FROM reports WHERE id NOT IN (SELECT id FROM reports ORDER BY created_at DESC LIMIT 200)')
        return record
    def list(self):
        with self.connect() as connection:
            return [dict(r) for r in connection.execute('SELECT id,created_at,project,title,kind,score FROM reports ORDER BY created_at DESC')]
    def get(self, report_id):
        with self.connect() as connection:
            row=connection.execute('SELECT report FROM reports WHERE id=?',(report_id,)).fetchone()
        return json.loads(row['report']) if row else None
    def delete(self, report_id):
        with self.connect() as connection:
            return connection.execute('DELETE FROM reports WHERE id=?',(report_id,)).rowcount > 0
