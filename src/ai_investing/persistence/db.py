from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from ai_investing.persistence.tables import Base


@dataclass(slots=True)
class Database:
    url: str
    engine: Engine = field(init=False)
    session_factory: sessionmaker[Session] = field(init=False)

    def __post_init__(self) -> None:
        engine_kwargs: dict[str, object] = {"future": True}
        if self.url == "sqlite+pysqlite:///:memory:":
            engine_kwargs["connect_args"] = {"check_same_thread": False}
            engine_kwargs["poolclass"] = StaticPool
        self.engine = create_engine(self.url, **engine_kwargs)
        self.session_factory = sessionmaker(bind=self.engine, autoflush=True, future=True)

    def initialize(self) -> None:
        if self._should_use_migrations():
            self._apply_migrations()
            return
        Base.metadata.create_all(self.engine)

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def ping(self) -> bool:
        """Return True if the database is reachable."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def _should_use_migrations(self) -> bool:
        if self.url == "sqlite+pysqlite:///:memory:":
            return False
        return Path("alembic.ini").is_file() and Path("alembic").is_dir()

    def _apply_migrations(self) -> None:
        from alembic import command
        from alembic.config import Config

        config = Config("alembic.ini")
        config.set_main_option("sqlalchemy.url", self.url)
        table_names = set(inspect(self.engine).get_table_names())
        if table_names and "alembic_version" not in table_names:
            command.stamp(config, "head")
            return
        command.upgrade(config, "head")
