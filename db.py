import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
DB_PATH = os.getenv("DB_PATH", "social_learning.db")
USE_POSTGRES = bool(DATABASE_URL and DATABASE_URL.startswith(("postgres://", "postgresql://")))

if USE_POSTGRES:
    import psycopg2


class DBRow:
    def __init__(self, row, column_names):
        self._row = row
        self._column_names = tuple(column_names)
        self._column_index = {name: idx for idx, name in enumerate(self._column_names)}

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._row[key]
        if isinstance(key, str):
            return self._row[self._column_index[key]]
        raise TypeError("Row indices must be integers or column names")

    def get(self, key, default=None):
        try:
            return self[key]
        except (KeyError, IndexError):
            return default

    def keys(self):
        return self._column_names

    def items(self):
        return ((name, self._row[idx]) for idx, name in enumerate(self._column_names))

    def __iter__(self):
        return iter(self._row)

    def __len__(self):
        return len(self._row)

    def __repr__(self):
        return f"<DBRow {dict(self.items())}>"


class DBCursor:
    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, query, params=None):
        if USE_POSTGRES:
            query = query.replace("?", "%s")
        if params is None:
            return self._cursor.execute(query)
        return self._cursor.execute(query, params)

    def executemany(self, query, params):
        if USE_POSTGRES:
            query = query.replace("?", "%s")
        return self._cursor.executemany(query, params)

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        if USE_POSTGRES:
            column_names = [desc[0] for desc in self._cursor.description]
            return DBRow(row, column_names)
        return row

    def fetchall(self):
        rows = self._cursor.fetchall()
        if not USE_POSTGRES:
            return rows
        column_names = [desc[0] for desc in self._cursor.description]
        return [DBRow(row, column_names) for row in rows]

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class DBConnection:
    def __init__(self, connection):
        self._connection = connection

    def cursor(self):
        return DBCursor(self._connection.cursor())

    def commit(self):
        return self._connection.commit()

    def rollback(self):
        return self._connection.rollback()

    def close(self):
        return self._connection.close()

    def __getattr__(self, name):
        return getattr(self._connection, name)


def is_postgres():
    return USE_POSTGRES


def get_connection():
    if USE_POSTGRES:
        connection = psycopg2.connect(DATABASE_URL)
        connection.autocommit = False
        return DBConnection(connection)

    connection = sqlite3.connect(DB_PATH, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = NORMAL")
    connection.execute("PRAGMA busy_timeout = 5000")
    connection.execute("PRAGMA temp_store = MEMORY")
    connection.execute("PRAGMA cache_size = -2000")
    return connection
