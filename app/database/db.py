import sqlite3
from datetime import datetime
from typing import List, Optional

class Database:
    def __init__(self, database_path: str = "files.db"):
        self.database_path = database_path
        self._create_tables()
    
    def _create_tables(self):
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT UNIQUE NOT NULL,
                    content TEXT,
                    downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_files_filename 
                ON files(filename)
            """)
            
            conn.commit()
    
    def add_file(self, filename: str, content: str) -> int:
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO files (filename, content, downloaded_at)
                VALUES (?, ?, ?)
            """, (filename, content, datetime.now().isoformat()))
            conn.commit()
            return cursor.lastrowid
    
    def add_files(self, files: List[tuple]) -> List[int]:
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT OR REPLACE INTO files (filename, content, downloaded_at)
                VALUES (?, ?, ?)
            """, files)
            conn.commit()
            ids = []
            for filename, _, _ in files:
                cursor.execute("SELECT id FROM files WHERE filename = ?", (filename,))
                result = cursor.fetchone()
                if result:
                    ids.append(result[0])
            return ids
    
    def get_all_files(self, limit: Optional[int] = None, offset: Optional[int] = 0) -> List[dict]:
        with sqlite3.connect(self.database_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT id, filename, downloaded_at FROM files ORDER BY downloaded_at DESC"
            
            if limit is not None:
                query += " LIMIT ? OFFSET ?"
                cursor.execute(query, (limit, offset))
            else:
                cursor.execute(query)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_files_by_names(self, names: List[str]) -> List[dict]:
        if not names:
            return []
        
        placeholders = ','.join(['?'] * len(names))
        with sqlite3.connect(self.database_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT id, filename, content, downloaded_at 
                FROM files 
                WHERE filename IN ({placeholders})
            """, names)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_total_count(self) -> int:
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM files")
            return cursor.fetchone()[0]
    
    def delete_file(self, filename: str):
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM files WHERE filename = ?", (filename,))
            conn.commit()
    
    def clear_all(self):
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM files")
            conn.commit()

    def file_exists(self, filename: str) -> bool:
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM files WHERE filename = ?", (filename,))
            return cursor.fetchone() is not None