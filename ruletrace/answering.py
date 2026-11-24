import json
import re
from time import perf_counter

from langchain_core.exceptions import OutputParserException
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import StructuredTool
from langchain_ollama import ChatOllama, OllamaEmbeddings
from pydantic import BaseModel, ConfigDict

from .config import Settings
from .model_revisions import model_digest
from .prompts import GROUNDED_ANSWER, TOOL_ROUTE
from .retrieval import Retriever
from .schema import Answer, Draft, Query, Registration, RegistrationID, RetrievalHit
from .storage import Store


class ModelOutputError(Exception):
    pass


class LookupArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    registration_id: RegistrationID


def registration_id_for(query: Query) -> str | None:
    discovered = set(re.findall(r"\bEVT-[0-9]{3}\b", query.question.upper()))
    if query.registration_id:
        discovered.add(query.registration_id)
    if len(discovered) > 1:
        raise ValueError("Multiple registrations are outside the supported scope")
    return next(iter(discovered), None)


def safe_draft(draft: Draft, hits: list[RetrievalHit]) -> tuple[str, list[RetrievalHit]] | None:
    if draft.status != "answered" or not draft.answer.strip() or not draft.citations:
        return None
    allowed = {f"E{index}": hit for index, hit in enumerate(hits, 1)}
    if not set(draft.citations).issubset(allowed):
        return None
    return draft.answer, [allowed[key] for key in dict.fromkeys(draft.citations)]


class Answering:
    def __init__(self, store: Store, retriever: Retriever, model: ChatOllama):
        self.store, self.retriever, self.model = store, retriever, model

    def lookup(self, expected_id: str) -> Registration | None:
        def lookup_registration(registration_id: str) -> dict | None:
            if registration_id != expected_id:
                raise ModelOutputError("Mismatched lookup ID")
            row = self.store.registration(registration_id)
            return row.model_dump() if row else None

        tool = StructuredTool.from_function(
            lookup_registration,
            args_schema=LookupArgs,
            description="Read the fictional festival registration category and status for a single ID.",
        )
        response = self.model.bind_tools([tool]).invoke(
            [
                SystemMessage(content=TOOL_ROUTE),
                HumanMessage(content=json.dumps({"registration_id": expected_id})),
            ]
        )
        calls = response.tool_calls
        if len(calls) != 1 or response.invalid_tool_calls or calls[0]["name"] != tool.name:
            raise ModelOutputError("Expected one supported tool call")
        try:
            arguments = LookupArgs.model_validate(calls[0]["args"])
        except ValueError as exc:
            raise ModelOutputError("Invalid tool arguments") from exc
        result = tool.invoke(arguments.model_dump())
        return Registration.model_validate(result) if result is not None else None

    def answer(self, query: Query) -> Answer:
        timings: dict[str, float] = {}
        registration = None
        generation = None

        def abstain(reason: str) -> Answer:
            return Answer(
                status="insufficient_evidence",
                reason=reason,
                answer="Não há evidência suficiente para responder a esta pergunta.",
                citations=[],
                registration=registration,
                generation_id=generation,
                timings_ms=timings,
            )

        try:
            registration_id = registration_id_for(query)
        except ValueError:
            return abstain("ambiguous_registration")
        if registration_id:
            started = perf_counter()
            try:
                registration = self.lookup(registration_id)
            except ModelOutputError:
                return abstain("tool_contract_rejected")
            finally:
                timings["tool"] = round((perf_counter() - started) * 1000, 2)
            if registration is None:
                return abstain("registration_not_found")
            if query.category is not None and query.category != registration.category:
                return abstain("category_mismatch")
        category = registration.category if registration else query.category or "geral"
        started = perf_counter()
        generation, hits = self.retriever.search(query, category)
        timings["retrieval"] = round((perf_counter() - started) * 1000, 2)
        if not hits:
            return abstain("no_retrieved_evidence")
        payload = {
            "question": query.question,
            "as_of": query.as_of.isoformat(),
            "category": category,
            "registration": registration.model_dump() if registration else None,
            "evidence": [
                {"id": f"E{index}", "section": hit.locator, "text": hit.content}
                for index, hit in enumerate(hits, 1)
            ],
        }
        started = perf_counter()
        try:
            draft = self.model.with_structured_output(Draft, method="json_schema").invoke(
                [
                    SystemMessage(content=GROUNDED_ANSWER),
                    HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
                ]
            )
        except (ValueError, TypeError, OutputParserException):
            return abstain("invalid_model_output")
        finally:
            timings["generation"] = round((perf_counter() - started) * 1000, 2)
        if isinstance(draft, Draft) and draft.status == "insufficient_evidence":
            return abstain("model_abstained")
        supported = safe_draft(draft, hits) if isinstance(draft, Draft) else None
        if supported is None:
            return abstain("no_valid_citations")
        answer, citations = supported
        return Answer(
            status="answered",
            answer=answer,
            citations=citations,
            registration=registration,
            generation_id=generation,
            timings_ms=timings,
        )


def build_service(settings: Settings) -> Answering:
    store = Store(settings.database)
    embeddings = OllamaEmbeddings(
        model=settings.embed_model, base_url=settings.ollama_url, client_kwargs={"timeout": 30.0}
    )
    model = ChatOllama(
        model=settings.chat_model,
        base_url=settings.ollama_url,
        temperature=0,
        num_ctx=4096,
        num_thread=6,
        num_predict=160,
        client_kwargs={"timeout": 100.0},
    )
    return Answering(
        store,
        Retriever(
            store,
            embeddings,
            settings.embed_model + "@" + model_digest(settings.ollama_url, settings.embed_model),
        ),
        model,
    )
