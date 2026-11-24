import os
from datetime import date
from pathlib import Path

import psycopg
import pytest

from ruletrace.ingestion import load_corpus
from ruletrace.retrieval import Retriever
from ruletrace.schema import Query
from ruletrace.storage import Store

pytestmark = pytest.mark.integration


def test_real_index_excludes_wrong_category_future_and_expired_rules():
    dsn = os.getenv("RULETRACE_TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("requires a dedicated database")
    assert os.getenv("RULETRACE_TEST_PROJECT") in {"ruletrace-ci", "ruletrace-qa"}
    store = Store(dsn)
    store.initialize()
    corpus = Path(__file__).resolve().parents[1] / "corpus"
    generation, chunks = load_corpus(corpus, "fixed-scope-vectors-v2")
    vector = [1.0] + [0.0] * 767
    # Vectors are controlled to test filters and fusion; model quality is a separate live eval.
    orthogonal = [0.0, 1.0] + [0.0] * 766
    vectors = [vector if chunk.rule.rule_id == "correcao" else orthogonal for chunk in chunks]
    store.publish(generation, "fixed-scope-vectors-v2", chunks, vectors)
    store.publish(generation, "fixed-scope-vectors-v2", chunks, vectors)
    assert store.current() == (generation, "fixed-scope-vectors-v2")
    registration = store.registration("EVT-042")
    assert registration is not None and registration.category == "expositor"
    assert store.registration("EVT-999") is None

    class ExplicitVectorsOnly:
        def embed_query(self, text: str) -> list[float]:
            raise AssertionError("integration should receive its query vector explicitly")

    engine = Retriever(store, ExplicitVectorsOnly(), "fixed-scope-vectors-v2")
    for mode in ("lexical", "semantic", "hybrid"):
        for scope, day, version in (
            ("expositor", date(2026, 5, 31), "1.0"),
            ("expositor", date(2026, 6, 1), "2.0"),
            ("oficineiro", date(2026, 6, 1), "1.0"),
        ):
            query = Query(question="corrigir inscrição incompleta", as_of=day, search=mode, top_k=8)
            _, hits = engine.search(query, scope, vector=vector)
            relevant = [hit for hit in hits if hit.rule_id == "correcao"]
            assert relevant and {hit.version for hit in relevant} == {version}, (
                mode,
                scope,
                day,
                hits,
            )
            assert all(scope in hit.locator for hit in relevant)
        query = Query(question="regulamento festival", as_of=date(2026, 1, 1), search=mode)
        assert engine.search(query, "expositor", vector=vector)[1] == []
    with store.connection() as conn:
        assert conn.execute(
            "SELECT count(*) FROM chunks WHERE generation_id = %s", (generation,)
        ).fetchone()[0] == len(chunks)

    dsn_reader = os.environ["RULETRACE_TEST_READER_URL"]
    reader = Store(dsn_reader)
    assert reader.current() == (generation, "fixed-scope-vectors-v2")
    with pytest.raises(psycopg.errors.InsufficientPrivilege), reader.connection() as conn:
        conn.execute("UPDATE active_corpus SET generation_id = %s", (generation,))
