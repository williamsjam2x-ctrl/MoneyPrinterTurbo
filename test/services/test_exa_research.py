from types import SimpleNamespace

import pytest
import requests

from app.services import exa_research


class FakeResponse:
    def __init__(self, payload, error=None):
        self.payload = payload
        self.error = error

    def raise_for_status(self):
        if self.error:
            raise self.error

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.response


def test_search_web_sends_bounded_moderated_request_and_normalizes_sources():
    session = FakeSession(
        FakeResponse(
            {
                "requestId": "request-123",
                "costDollars": {"total": 0.004},
                "searchTime": 1.25,
                "results": [
                    {
                        "title": "Official research",
                        "url": "https://example.com/report",
                        "publishedDate": "2026-11-01T00:00:00Z",
                        "author": "Research Team",
                        "highlights": ["Evidence excerpt"],
                    },
                    {"title": "Unsafe URL", "url": "http://example.com"},
                    {"url": "https://example.com/no-title"},
                    None,
                ],
            }
        )
    )

    result = exa_research.search_web(
        "AI video automation trends",
        num_results=5,
        start_published_date="2026-10-01T00:00:00Z",
        include_domains=["example.com"],
        api_key="private-test-key",
        session=session,
    )

    args, kwargs = session.calls[0]
    assert args == (exa_research.EXA_SEARCH_URL,)
    assert kwargs["headers"]["x-api-key"] == "private-test-key"
    assert kwargs["timeout"] == 20.0
    assert kwargs["json"] == {
        "query": "AI video automation trends",
        "type": "auto",
        "numResults": 5,
        "moderation": True,
        "contents": {"highlights": True},
        "startPublishedDate": "2026-10-01T00:00:00Z",
        "includeDomains": ["example.com"],
    }
    assert len(result.sources) == 1
    assert result.sources[0].title == "Official research"
    assert result.sources[0].highlights == ("Evidence excerpt",)
    assert result.estimated_cost_usd == 0.004
    assert result.request_id == "request-123"


def test_search_web_reads_key_from_environment(monkeypatch):
    monkeypatch.setenv("EXA_API_KEY", "environment-key")
    session = FakeSession(FakeResponse({"results": []}))

    exa_research.search_web("test query", session=session)

    assert session.calls[0][1]["headers"]["x-api-key"] == "environment-key"


@pytest.mark.parametrize(
    ("query", "kwargs", "message"),
    [
        (" ", {}, "non-empty"),
        ("x" * 1001, {}, "1000 characters"),
        ("query", {"num_results": 0}, "between 1 and 10"),
        ("query", {"num_results": True}, "integer"),
        ("query", {"timeout": 0}, "positive number"),
        ("query", {"include_domains": "example.com"}, "sequence"),
        ("query", {"include_domains": [""]}, "non-empty strings"),
        ("query", {"include_domains": ["example.com"] * 21}, "20 domains"),
    ],
)
def test_search_web_rejects_invalid_input(query, kwargs, message):
    with pytest.raises(ValueError, match=message):
        exa_research.search_web(query, api_key="test-key", **kwargs)


def test_search_web_requires_api_key(monkeypatch):
    monkeypatch.delenv("EXA_API_KEY", raising=False)

    with pytest.raises(exa_research.ExaResearchError, match="not configured"):
        exa_research.search_web("test query")


def test_search_web_wraps_http_failures_without_exposing_credentials():
    error = requests.Timeout("request timed out")
    session = FakeSession(FakeResponse({}, error=error))

    with pytest.raises(exa_research.ExaResearchError, match="Timeout") as caught:
        exa_research.search_web(
            "test query", api_key="secret-value", session=session
        )

    assert "secret-value" not in str(caught.value)


def test_search_web_rejects_malformed_api_responses():
    session = FakeSession(FakeResponse({"error": "bad request"}))

    with pytest.raises(exa_research.ExaResearchError, match="API error"):
        exa_research.search_web("test query", api_key="test-key", session=session)

    session = FakeSession(FakeResponse({"results": "not-a-list"}))
    with pytest.raises(exa_research.ExaResearchError, match="results list"):
        exa_research.search_web("test query", api_key="test-key", session=session)
