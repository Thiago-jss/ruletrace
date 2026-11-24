import logging
from functools import lru_cache

import httpx
import ollama
import psycopg
from fastapi import FastAPI, HTTPException
from langchain_core.exceptions import OutputParserException

from .answering import build_service
from .config import Settings
from .schema import Answer, Query
from .storage import IndexUnavailable

app = FastAPI(title="RuleTrace", version="0.1.0", description="Demo local com dados fictícios.")
logger = logging.getLogger("ruletrace")


@lru_cache
def service():
    return build_service(Settings.local())


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", response_model=Answer)
def ask(query: Query):
    try:
        return service().answer(query)
    except (
        IndexUnavailable,
        psycopg.Error,
        httpx.HTTPError,
        ollama.ResponseError,
        ConnectionError,
        OutputParserException,
    ) as error:
        logger.warning("request_dependency_error type=%s", type(error).__name__)
        raise HTTPException(
            status_code=503, detail="Uma dependência local está indisponível."
        ) from error
