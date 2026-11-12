"""Cost-conscious Exa search adapter for the optional intelligence layer.

This adapter only retrieves research sources. It does not make factual claims,
score opportunities, generate scripts, or trigger video production.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Sequence

import requests


EXA_SEARCH_URL = "https://api.exa.ai/search"
DEFAULT_TIMEOUT_SECONDS = 20.0
DEFAULT_NUM_RESULTS = 8
MAX_NUM_RESULTS = 10
MAX_QUERY_CHARS = 1_000


class ExaResearchError(RuntimeError):
    """Raised when Exa search cannot return a usable research response."""


@dataclass(frozen=True, slots=True)
class ResearchSource:
    title: str
    url: str
    published_date: str | None
    author: str | None
    highlights: tuple[str, ...]
    summary: str | None


@dataclass(frozen=True, slots=True)
class ResearchSearchResult:
    query: str
    sources: tuple[ResearchSource, ...]
    request_id: str | None
    estimated_cost_usd: float | None
    search_time_seconds: float | None


def _optional_string(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _parse_source(item: Any) -> ResearchSource | None:
    if not isinstance(item, dict):
        return None

    title = _optional_string(item.get("title"))
    url = _optional_string(item.get("url"))
    if not title or not url or not url.startswith("https://"):
        return None

    raw_highlights = item.get("highlights")
    highlights = (
        tuple(text.strip() for text in raw_highlights if isinstance(text, str) and text.strip())
        if isinstance(raw_highlights, list)
        else ()
    )
    return ResearchSource(
        title=title,
        url=url,
        published_date=_optional_string(item.get("publishedDate")),
        author=_optional_string(item.get("author")),
        highlights=highlights,
        summary=_optional_string(item.get("summary")),
    )


def search_web(
    query: str,
    *,
    num_results: int = DEFAULT_NUM_RESULTS,
    start_published_date: str | None = None,
    include_domains: Sequence[str] | None = None,
    api_key: str | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    session: Any = None,
) -> ResearchSearchResult:
    """Search Exa and return normalized, citation-ready source metadata.

    The API key is read from EXA_API_KEY unless explicitly supplied by the
    caller. Keys are sent only in the x-api-key header and are never returned.
    """
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string.")
    query = query.strip()
    if len(query) > MAX_QUERY_CHARS:
        raise ValueError(f"query must not exceed {MAX_QUERY_CHARS} characters.")
    if isinstance(num_results, bool) or not isinstance(num_results, int):
        raise ValueError("num_results must be an integer.")
    if not 1 <= num_results <= MAX_NUM_RESULTS:
        raise ValueError(f"num_results must be between 1 and {MAX_NUM_RESULTS}.")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ValueError("timeout must be a positive number.")

    domains: list[str] | None = None
    if include_domains is not None:
        if isinstance(include_domains, str):
            raise ValueError("include_domains must be a sequence of domain strings.")
        domains = list(include_domains)
        if any(not isinstance(domain, str) or not domain.strip() for domain in domains):
            raise ValueError("include_domains must contain non-empty strings.")
        domains = [domain.strip() for domain in domains]
        if len(domains) > 20:
            raise ValueError("include_domains must not contain more than 20 domains.")

    key = (api_key or os.getenv("EXA_API_KEY", "")).strip()
    if not key:
        raise ExaResearchError("EXA_API_KEY is not configured.")

    payload: dict[str, Any] = {
        "query": query,
        "type": "auto",
        "numResults": num_results,
        "moderation": True,
        "contents": {"highlights": True},
    }
    if start_published_date:
        payload["startPublishedDate"] = start_published_date
    if domains:
        payload["includeDomains"] = domains

    client = session if session is not None else requests
    try:
        response = client.post(
            EXA_SEARCH_URL,
            headers={"x-api-key": key, "Content-Type": "application/json"},
            json=payload,
            timeout=float(timeout),
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise ExaResearchError(f"Exa search request failed: {type(exc).__name__}.") from exc
    except ValueError as exc:
        raise ExaResearchError("Exa returned invalid JSON.") from exc

    if not isinstance(data, dict):
        raise ExaResearchError("Exa returned an unexpected response format.")
    if data.get("error"):
        raise ExaResearchError("Exa search returned an API error.")

    raw_sources = data.get("results")
    if not isinstance(raw_sources, list):
        raise ExaResearchError("Exa response did not contain a results list.")

    sources = tuple(
        source
        for source in (_parse_source(item) for item in raw_sources)
        if source is not None
    )
    cost_data = data.get("costDollars")
    raw_cost = cost_data.get("total") if isinstance(cost_data, dict) else None
    raw_time = data.get("searchTime")

    return ResearchSearchResult(
        query=query,
        sources=sources,
        request_id=_optional_string(data.get("requestId")),
        estimated_cost_usd=(
            float(raw_cost)
            if isinstance(raw_cost, (int, float)) and not isinstance(raw_cost, bool)
            else None
        ),
        search_time_seconds=(
            float(raw_time)
            if isinstance(raw_time, (int, float)) and not isinstance(raw_time, bool)
            else None
        ),
    )
