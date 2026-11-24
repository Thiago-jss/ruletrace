import argparse
import json
from pathlib import Path

from langchain_ollama import OllamaEmbeddings

from .config import Settings
from .ingestion import load_corpus
from .model_revisions import model_digest
from .storage import Store


def ingest(path: Path) -> None:
    settings = Settings.local()
    store = Store(settings.database)
    store.initialize()
    revision = settings.embed_model + "@" + model_digest(settings.ollama_url, settings.embed_model)
    generation, chunks = load_corpus(path, revision)
    if store.has_generation(generation):
        store.activate(generation)
        state = "reused"
    else:
        embedder = OllamaEmbeddings(
            model=settings.embed_model,
            base_url=settings.ollama_url,
            client_kwargs={"timeout": 100.0},
        )
        vectors = []
        for offset in range(0, len(chunks), 16):
            vectors.extend(
                embedder.embed_documents([chunk.content for chunk in chunks[offset : offset + 16]])
            )
        store.publish(generation, revision, chunks, vectors)
        state = "built"
    print(json.dumps({"generation": generation, "chunks": len(chunks), "state": state}))


def main() -> None:
    parser = argparse.ArgumentParser(prog="ruletrace")
    parser.add_argument("command", choices=["ingest", "evaluate"])
    parser.add_argument("--corpus", type=Path, default=Path("corpus"))
    parser.add_argument("--generation-eval", action="store_true")
    parser.add_argument(
        "--case", action="append", default=None, help="Run a named case; repeat to select a subset"
    )
    args = parser.parse_args()
    if args.command == "ingest":
        ingest(args.corpus)
    else:
        from .evaluation import evaluate

        evaluate(args.generation_eval, args.case)


if __name__ == "__main__":
    main()
