import hashlib
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from langchain_text_splitters import CharacterTextSplitter, RecursiveCharacterTextSplitter
from pypdf import PdfReader

from .schema import Manifest, RuleSource, Strategy

CHUNKING_REVISION = "1"
MAX_BYTES = 500_000
MAX_TEXT = 150_000
SECTION_SIZE = 620
WINDOW_SIZE = 320
WINDOW_OVERLAP = 60


@dataclass(frozen=True)
class Chunk:
    id: str
    strategy: Strategy
    rule: RuleSource
    locator: str
    content: str


def validate_versions(manifest: Manifest) -> None:
    groups: dict[tuple[str, str], list[RuleSource]] = defaultdict(list)
    revisions: set[tuple[str, str, str]] = set()
    for source in manifest.sources:
        key = (source.rule_id, source.category, source.version)
        if key in revisions:
            raise ValueError(f"reused version for {source.rule_id}")
        revisions.add(key)
        groups[key[:2]].append(source)
    for sources in groups.values():
        ordered = sorted(sources, key=lambda source: source.starts_on)
        for previous, following in zip(ordered, ordered[1:], strict=False):
            if previous.ends_on is None or previous.ends_on > following.starts_on:
                raise ValueError(f"overlapping versions for {previous.rule_id}")


def markdown_sections(text: str) -> list[tuple[str, str]]:
    pieces = []
    locator, body = "Preâmbulo", []
    for line in text.splitlines():
        if re.match(r"^#{1,6} ", line):
            if "\n".join(body).strip():
                pieces.append((locator, "\n".join(body).strip()))
            locator = line.lstrip("# ").strip()
            body = []
        else:
            body.append(line)
    if "\n".join(body).strip():
        pieces.append((locator, "\n".join(body).strip()))
    return pieces


def source_path(root: Path, name: str) -> Path:
    relative = Path(name)
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or relative.suffix.lower() not in {".md", ".pdf"}
    ):
        raise ValueError("manifest paths must be relative Markdown or PDF files")
    path = (root / relative).resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError("source must be a bounded file inside the corpus")
    return path


def regions(path: Path) -> list[tuple[str, str]]:
    if path.suffix.lower() == ".md":
        result = markdown_sections(path.read_text(encoding="utf-8"))
    else:
        reader = PdfReader(path)
        if reader.is_encrypted or len(reader.pages) > 40:
            raise ValueError("only small, unencrypted textual PDFs are supported")
        result = [
            (f"Página {number}", text)
            for number, page in enumerate(reader.pages, 1)
            if (text := (page.extract_text() or "").strip())
        ]
    if not result or sum(len(text) for _, text in result) > MAX_TEXT:
        raise ValueError("source has no extractable text or exceeds the text limit")
    return result


def load_corpus(root: Path, embedding_revision: str) -> tuple[str, list[Chunk]]:
    root = root.resolve(strict=True)
    manifest = Manifest.model_validate_json((root / "manifest.json").read_bytes())
    validate_versions(manifest)
    hash_parts = [CHUNKING_REVISION, embedding_revision, manifest.model_dump_json()]
    chunks = []
    section_split = RecursiveCharacterTextSplitter(chunk_size=SECTION_SIZE, chunk_overlap=0)
    window_split = CharacterTextSplitter(
        separator="", chunk_size=WINDOW_SIZE, chunk_overlap=WINDOW_OVERLAP
    )
    for rule in manifest.sources:
        path = source_path(root, rule.file)
        hash_parts.append(hashlib.sha256(path.read_bytes()).hexdigest())
        for position, (locator, content) in enumerate(regions(path)):
            for strategy, splitter in (("section", section_split), ("window", window_split)):
                for part, text in enumerate(splitter.split_text(content)):
                    key = json.dumps(
                        [rule.rule_id, rule.version, rule.category, position, part, strategy]
                    )
                    chunk_id = hashlib.sha256(key.encode()).hexdigest()[:24]
                    chunks.append(Chunk(chunk_id, strategy, rule, locator, text))
    generation = hashlib.sha256(json.dumps(hash_parts).encode()).hexdigest()
    return generation, chunks
