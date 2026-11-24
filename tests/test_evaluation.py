from ruletrace.evaluation import score_answer
from ruletrace.schema import Answer


def test_abstention_cannot_pass_factual_check_by_substring():
    case = {"id": "negation", "expected_status": "answered", "terms": [["não"]]}
    outcome = Answer(
        status="insufficient_evidence", answer="Não há evidência suficiente.", citations=[]
    )
    scored = score_answer(case, outcome)
    assert scored["status_match"] is False
    assert scored["fact_proxy_match"] is False


def test_supported_lexical_proxy_does_not_claim_an_expected_source_without_one():
    case = {
        "id": "code",
        "expected_status": "answered",
        "terms": [["L-17"]],
        "source": ["transport", "1.0", "Art. 6"],
    }
    outcome = Answer(status="answered", answer="Use o portão L-17.", citations=[])
    scored = score_answer(case, outcome)
    assert scored["fact_proxy_match"] is True
    assert scored["expected_source_cited"] is False
