from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import psycopg
from psycopg.rows import dict_row


class Database:
    """Small connection-per-operation wrapper for the POC.

    The durable queue uses PostgreSQL row locking in the repository layer. A pool is
    intentionally deferred until measured concurrency requires one.
    """

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    @contextmanager
    def connection(self) -> Iterator[Any]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            yield connection

    def ping(self) -> bool:
        try:
            with self.connection() as connection:
                connection.execute("SELECT 1")
            return True
        except psycopg.Error:
            return False
