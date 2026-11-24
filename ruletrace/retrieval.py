from collections import defaultdict
from typing import Protocol

from .schema import Category, Query, RetrievalHit
from .storage import IndexUnavailable, Store


class Embeddings(Protocol):
    def embed_query(self, text: str) -> list[float]: ...


def fuse(rankings: list[list[RetrievalHit]], constant: int = 60) -> list[RetrievalHit]:
    scores: dict[str, float] = defaultdict(float)
    hits: dict[str, RetrievalHit] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, 1):
            hits[item.chunk_id] = item
            scores[item.chunk_id] += 1 / (constant + rank)
    return [hits[key] for key in sorted(hits, key=lambda key: (-scores[key], key))]


class Retriever:
    def __init__(self, store: Store, embeddings: Embeddings, model: str):
        self.store, self.embeddings, self.model = store, embeddings, model

    def search(
        self,
        query: Query,
        category: Category,
        *,
        vector: list[float] | None = None,
        snapshot: tuple[str, str] | None = None,
    ) -> tuple[str, list[RetrievalHit]]:
        generation, indexed_model = snapshot or self.store.current()
        if indexed_model != self.model:
            raise IndexUnavailable(
                "Embedding revision differs from the active corpus; reindex first"
            )
        if query.search != "lexical" and vector is None:
            vector = self.embeddings.embed_query(query.question)
        lexical, semantic = self.store.candidates(
            generation=generation,
            strategy=query.chunking,
            category=category,
            as_of=query.as_of,
            mode=query.search,
            query=query.question,
            vector=vector,
            limit=query.top_k * 3,
        )
        hits = (
            fuse([lexical, semantic])
            if query.search == "hybrid"
            else lexical
            if query.search == "lexical"
            else semantic
        )
        return generation, hits[: query.top_k]
