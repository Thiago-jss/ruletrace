import json
import statistics
from itertools import product
from pathlib import Path
from time import perf_counter

from .answering import build_service
from .config import Settings
from .model_revisions import model_digest
from .prompts import PROMPT_REVISION
from .schema import Query, RetrievalHit


def source_id(hit: RetrievalHit) -> tuple[str, str, str]:
    return hit.rule_id, hit.version, hit.locator


def evaluate(generation_eval: bool) -> None:
    settings = Settings.local()
    service = build_service(settings)
    data_path = Path(__file__).resolve().parents[1] / "evals/questions.json"
    dataset = json.loads(data_path.read_text(encoding="utf-8"))
    snapshot = service.store.current()
    k = 4
    retrieval = []
    for case in dataset:
        if not case.get("source"):
            continue
        inputs = {key: value for key, value in case.items() if key in Query.model_fields}
        vector = service.retriever.embeddings.embed_query(case["question"])
        for mode, strategy in product(("lexical", "semantic", "hybrid"), ("section", "window")):
            query = Query(**inputs, search=mode, chunking=strategy, top_k=k)
            started = perf_counter()
            _, hits = service.retriever.search(
                query, query.category or "geral", vector=vector, snapshot=snapshot
            )
            target = tuple(case["source"])
            rank = next((i for i, hit in enumerate(hits, 1) if source_id(hit) == target), None)
            retrieval.append(
                {
                    "case": case["id"],
                    "mode": mode,
                    "chunking": strategy,
                    "rank": rank,
                    "sources": [source_id(hit) for hit in hits],
                    "search_ms_excluding_embedding": round((perf_counter() - started) * 1000, 2),
                }
            )
    summaries = []
    for mode, strategy in product(("lexical", "semantic", "hybrid"), ("section", "window")):
        items = [row for row in retrieval if row["mode"] == mode and row["chunking"] == strategy]
        summaries.append(
            {
                "mode": mode,
                "chunking": strategy,
                "k": k,
                "count": len(items),
                "recall_at_k": round(statistics.mean(row["rank"] is not None for row in items), 4),
                "mrr_at_k": round(
                    statistics.mean(1 / row["rank"] if row["rank"] else 0 for row in items), 4
                ),
                "median_search_ms_excluding_embedding": round(
                    statistics.median(row["search_ms_excluding_embedding"] for row in items), 2
                ),
            }
        )
    answers = []
    if generation_eval:
        for case in dataset:
            inputs = {key: value for key, value in case.items() if key in Query.model_fields}
            query = Query(**inputs, top_k=k)
            response = service.answer(query)
            if response.generation_id and response.generation_id != snapshot[0]:
                raise RuntimeError("Corpus changed during generation evaluation")
            expected_source = tuple(case.get("source", []))
            source_match = any(source_id(hit) == expected_source for hit in response.citations)
            # This is intentionally only a regression proxy, not a judge of entailment.
            facts = all(
                any(term.casefold() in response.answer.casefold() for term in alternatives)
                for alternatives in case.get("terms", [])
            )
            if case["expected_status"] == "insufficient_evidence":
                facts = not response.citations and response.status == "insufficient_evidence"
            answers.append(
                {
                    "case": case["id"],
                    "expected_status": case["expected_status"],
                    "expected_source": list(expected_source),
                    "status_match": response.status == case["expected_status"],
                    "expected_source_cited": source_match if expected_source else None,
                    "fact_proxy_match": facts,
                    "response": response.model_dump(mode="json"),
                }
            )
    print(
        json.dumps(
            {
                "generation": snapshot[0],
                "embedding_model": snapshot[1],
                "chat_model": settings.chat_model,
                "chat_model_digest": model_digest(settings.ollama_url, settings.chat_model)
                if generation_eval
                else None,
                "prompt_revision": PROMPT_REVISION,
                "retrieval_summary": summaries,
                "retrieval_per_case": retrieval,
                "answers": answers,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
