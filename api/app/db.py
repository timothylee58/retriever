from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

def _schema_path() -> Path:
    here = Path(__file__).resolve()
    for candidate in (here.parents[2] / "sql" / "0001_schema.sql", here.parents[1] / "sql" / "0001_schema.sql"):
        if candidate.exists():
            return candidate
    raise FileNotFoundError("sql/0001_schema.sql")


def make_engine(url: str) -> Engine:
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return create_engine(url, future=True)


def apply_schema(engine: Engine) -> None:
    sql = _schema_path().read_text()
    raw = engine.raw_connection()
    try:
        raw.cursor().execute(sql)
        raw.commit()
    finally:
        raw.close()


def fetch_one(engine: Engine, sql: str, params: dict | None = None):
    with engine.connect() as conn:
        return conn.execute(text(sql), params or {}).mappings().first()


def fetch_all(engine: Engine, sql: str, params: dict | None = None):
    with engine.connect() as conn:
        return list(conn.execute(text(sql), params or {}).mappings())
