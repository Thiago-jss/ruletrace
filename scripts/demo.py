import json
import os
from urllib.request import Request, urlopen

base = os.getenv("RULETRACE_API_URL", "http://127.0.0.1:8120").rstrip("/")


def ask(question, as_of, **kwargs):
    body = json.dumps({"question": question, "as_of": as_of, **kwargs}).encode()
    request = Request(base + "/ask", data=body, headers={"content-type": "application/json"})
    with urlopen(request, timeout=110) as response:
        return json.load(response)


current = ask("Ainda posso corrigir a inscrição EVT-042?", "2026-06-03")
assert current["status"] == "answered", current
assert current["registration"] == {"id": "EVT-042", "category": "expositor", "status": "incompleta"}
assert any(
    item["rule_id"] == "correcao" and item["version"] == "2.0" for item in current["citations"]
)
assert "15 de junho" in current["answer"] or "15/06" in current["answer"]

old = ask(
    "Um expositor podia corrigir uma inscrição incompleta?", "2026-05-20", category="expositor"
)
assert old["status"] == "answered", old
assert any(item["rule_id"] == "correcao" and item["version"] == "1.0" for item in old["citations"])
assert all(item["version"] != "2.0" for item in old["citations"])

missing = ask("Qual será o valor do estacionamento na edição de 2027?", "2026-06-03")
assert missing["status"] == "insufficient_evidence" and not missing["citations"], missing

for label, item in (
    ("Regra vigente e consulta da inscrição", current),
    ("Regra histórica", old),
    ("Fora do corpus", missing),
):
    print(label + ": " + item["answer"])
    for citation in item["citations"]:
        print(f"  ↳ {citation['source']} v{citation['version']} — {citation['locator']}")
