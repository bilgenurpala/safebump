import sqlite3
from contextlib import contextmanager
from pathlib import Path

DATABASE_PATH = Path(__file__).resolve().parent / "tasks.db"

SEED_TASKS = (
    ("Learn FastAPI", 0),
    ("Connect the API to SQLite", 0),
    ("Test data persistence", 0),
)


@contextmanager
def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def initialize_database():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1))
            )
            """
        )
        task_count = connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        if task_count == 0:
            connection.executemany(
                "INSERT INTO tasks (title, done) VALUES (?, ?)",
                SEED_TASKS,
            )

