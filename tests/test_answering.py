from datetime import date
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage

from ruletrace.answering import Answering, ModelOutputError, registration_id_for, safe_draft
from ruletrace.retrieval import fuse
from ruletrace.schema import Draft, Query, RetrievalHit


def hit(identifier: str) -> RetrievalHit:
    return RetrievalHit(
        chunk_id=identifier,
        rule_id="rule",
        version="1.0",
        source="doc.md",
        locator="A",
        content="source",
    )


def test_rank_fusion_rewards_agreement_and_deduplicates():
    a, b, c = (hit(i) for i in ("a", "b", "c"))
    assert fuse([[a, b], [c, b]]) == [b, a, c]


def test_citation_gate_rejects_invented_and_empty_citations():
    evidence = [hit("a"), hit("b")]
    assert (
        safe_draft(
            Draft(status="answered", answer="answer", citations=["E1", "invented"]), evidence
        )
        is None
    )
    assert safe_draft(Draft(status="answered", answer="answer"), evidence) is None
    assert safe_draft(
        Draft(status="answered", answer="answer", citations=["E2", "E2"]), evidence
    ) == ("answer", [evidence[1]])


def fake_model(calls):
    return SimpleNamespace(
        bind_tools=lambda _tools: SimpleNamespace(
            invoke=lambda _messages: AIMessage(content="", tool_calls=calls)
        )
    )


def fake_call(value, name="lookup_registration"):
    return {"name": name, "args": {"registration_id": value}, "id": "call-1"}


@pytest.mark.parametrize(
    "calls",
    [
        [fake_call("EVT-073")],
        [fake_call("EVT-042", "other")],
        [fake_call("EVT-042"), fake_call("EVT-042")],
        [],
    ],
)
def test_denies_unapproved_calls_before_storage(calls):
    def unexpected_lookup(_):
        pytest.fail("storage should not run")

    service = Answering(SimpleNamespace(registration=unexpected_lookup), None, fake_model(calls))
    with pytest.raises(ModelOutputError):
        service.lookup("EVT-042")


def test_registration_id_is_bound_to_the_user_request():
    query = Query(question="Posso corrigir a EVT-042?", as_of=date(2026, 6, 2))
    assert registration_id_for(query) == "EVT-042"
    with pytest.raises(ValueError, match="Multiple registrations"):
        registration_id_for(query.model_copy(update={"registration_id": "EVT-073"}))
