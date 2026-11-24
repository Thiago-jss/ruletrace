from datetime import date
from pathlib import Path

import pytest

from ruletrace.ingestion import load_corpus, source_path, validate_versions
from ruletrace.schema import Manifest, RuleSource

CORPUS = Path(__file__).resolve().parents[1] / "corpus"


def test_ingestion_is_deterministic_and_tracks_pdf_pages():
    generation, chunks = load_corpus(CORPUS, "model")
    assert load_corpus(CORPUS, "model") == (generation, chunks)
    assert load_corpus(CORPUS, "other-model")[0] != generation
    assert {chunk.strategy for chunk in chunks} == {"window", "section"}
    assert len({chunk.id for chunk in chunks}) == len(chunks)
    assert any(chunk.locator == "Página 1" and "07h15" in chunk.content for chunk in chunks)
    power = [chunk for chunk in chunks if chunk.locator == "Art. 3 — Energia"]
    assert sum(chunk.strategy == "section" for chunk in power) == 1
    assert sum(chunk.strategy == "window" for chunk in power) == 2
    assert max(len(chunk.content) for chunk in power if chunk.strategy == "window") <= 320


def test_rejects_overlapping_versions_for_same_category():
    rule = RuleSource(
        rule_id="regra",
        version="1.0",
        category="geral",
        starts_on=date(2026, 1, 1),
        file="fixture.md",
    )
    next_rule = rule.model_copy(update={"version": "2.0", "starts_on": date(2026, 6, 1)})
    with pytest.raises(ValueError, match="overlapping"):
        validate_versions(Manifest(sources=[rule, next_rule]))


def test_manifest_cannot_escape_via_relative_path_or_symlink(tmp_path):
    inside = tmp_path / "inside"
    inside.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("outside")
    (inside / "outside.md").symlink_to(outside)
    for name in ("../outside.md", "outside.md", str(outside)):
        with pytest.raises(ValueError):
            source_path(inside, name)
