from datetime import date
from pathlib import Path

import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row

from .ingestion import Chunk
from .schema import Category, Registration, RetrievalHit, SearchMode, Strategy

ROOT = Path(__file__).resolve().parents[1]
DIMENSIONS = 768


class IndexUnavailable(Exception):
    pass


class Store:
    def __init__(self, dsn: str):
        self.dsn = dsn

    def connection(self):
        return psycopg.connect(self.dsn, connect_timeout=4, options="-c statement_timeout=7000")

    def initialize(self) -> None:
        with self.connection() as conn:
            conn.execute((ROOT / "sql/001_schema.sql").read_text(encoding="utf-8"))

    def has_generation(self, generation: str) -> bool:
        with self.connection() as conn:
            return (
                conn.execute(
                    "SELECT 1 FROM corpus_generations WHERE id = %s", (generation,)
                ).fetchone()
                is not None
            )

    def publish(
        self, generation: str, model: str, chunks: list[Chunk], vectors: list[list[float]]
    ) -> None:
        if len(chunks) != len(vectors) or any(len(vector) != DIMENSIONS for vector in vectors):
            raise ValueError("unexpected embedding dimensions or batch size")
        with self.connection() as conn:
            register_vector(conn)
            created = conn.execute(
                "INSERT INTO corpus_generations (id, embedding_model) VALUES (%s,%s) ON CONFLICT DO NOTHING RETURNING id",
                (generation, model),
            ).fetchone()
            if created:
                with conn.cursor() as cursor:
                    cursor.executemany(
                        """INSERT INTO chunks (generation_id, strategy, chunk_id, rule_id, version, source, locator,
                      category, starts_on, ends_on, content, embedding) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::vector)""",
                        [
                            (
                                generation,
                                chunk.strategy,
                                chunk.id,
                                chunk.rule.rule_id,
                                chunk.rule.version,
                                chunk.rule.file,
                                chunk.locator,
                                chunk.rule.category,
                                chunk.rule.starts_on,
                                chunk.rule.ends_on,
                                chunk.content,
                                vector,
                            )
                            for chunk, vector in zip(chunks, vectors, strict=True)
                        ],
                    )
            self._activate(conn, generation)

    def activate(self, generation: str) -> None:
        with self.connection() as conn:
            self._activate(conn, generation)

    @staticmethod
    def _activate(conn, generation: str) -> None:
        conn.execute(
            """INSERT INTO active_corpus (singleton, generation_id) VALUES (true,%s)
          ON CONFLICT (singleton) DO UPDATE SET generation_id = EXCLUDED.generation_id""",
            (generation,),
        )

    def current(self) -> tuple[str, str]:
        with self.connection() as conn:
            row = conn.execute("""SELECT g.id, g.embedding_model FROM active_corpus a
                JOIN corpus_generations g ON g.id = a.generation_id WHERE a.singleton""").fetchone()
        if row is None:
            raise IndexUnavailable("No corpus has been activated")
        return row[0], row[1]

    def registration(self, registration_id: str) -> Registration | None:
        with self.connection() as conn, conn.cursor(row_factory=dict_row) as cursor:
            row = cursor.execute(
                "SELECT id, category, status FROM registration_fixtures WHERE id = %s",
                (registration_id,),
            ).fetchone()
        return Registration.model_validate(row) if row else None

    def candidates(
        self,
        *,
        generation: str,
        strategy: Strategy,
        category: Category,
        as_of: date,
        mode: SearchMode,
        query: str,
        vector: list[float] | None,
        limit: int,
    ) -> tuple[list[RetrievalHit], list[RetrievalHit]]:
        scopes = (generation, strategy, category, as_of, as_of)
        conditions = "generation_id = %s AND strategy = %s AND category IN ('geral', %s) AND starts_on <= %s AND (ends_on IS NULL OR ends_on > %s)"
        columns = "chunk_id, rule_id, version, source, locator, content"
        lexical, semantic = [], []
        with self.connection() as conn, conn.cursor(row_factory=dict_row) as cursor:
            if mode in ("lexical", "hybrid"):
                # SQL syntax is fixed; user input is bound as data, including the lexical query.
                rows = cursor.execute(
                    f"""WITH words AS (
                          SELECT unnest(tsvector_to_array(to_tsvector('portuguese', %s))) AS word
                        ), q AS (SELECT to_tsquery('simple', coalesce(string_agg(quote_literal(word), ' | '), '')) AS term FROM words)
                     SELECT {columns} FROM chunks CROSS JOIN q WHERE {conditions} AND lexical @@ term
                     ORDER BY ts_rank_cd(lexical, term) DESC, chunk_id LIMIT %s""",
                    (query, *scopes, limit),
                ).fetchall()
                lexical = [RetrievalHit.model_validate(row) for row in rows]
            if mode in ("semantic", "hybrid"):
                if vector is None or len(vector) != DIMENSIONS:
                    raise ValueError("invalid query embedding dimensions")
                register_vector(conn)
                rows = cursor.execute(
                    f"""SELECT {columns} FROM chunks WHERE {conditions}
                     ORDER BY embedding <=> %s::vector, chunk_id LIMIT %s""",
                    (*scopes, vector, limit),
                ).fetchall()
                semantic = [RetrievalHit.model_validate(row) for row in rows]
        return lexical, semantic
