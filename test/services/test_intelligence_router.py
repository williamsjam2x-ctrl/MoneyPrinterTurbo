from types import SimpleNamespace

import pytest

from app.services import intelligence_router as router


def _response(content: str):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(prompt_tokens=12, completion_tokens=7),
    )


def test_generate_text_uses_configured_provider(monkeypatch):
    monkeypatch.setenv("CODECRAFT_API_KEY", "test-key")
    monkeypatch.setenv("CODECRAFT_MODEL", "test-model")

    class FakeClient:
        def __init__(self, **kwargs):
            assert kwargs["base_url"] == "https://codecraftapi.com/v1"
            assert kwargs["max_retries"] == 0
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **kwargs: _response("  Draft script  ")
                )
            )

    monkeypatch.setattr(router, "OpenAI", FakeClient)
    result = router.generate_text(
        task="script_draft",
        system_prompt="Write a concise script.",
        user_prompt="Explain how AI automation saves time.",
        provider_order=("codecraft",),
    )

    assert result.content == "Draft script"
    assert result.provider == "codecraft"
    assert result.model == "test-model"
    assert result.prompt_tokens == 12
    assert result.completion_tokens == 7


def test_generate_text_falls_back_after_provider_error(monkeypatch):
    monkeypatch.setenv("CODECRAFT_API_KEY", "codecraft-key")
    monkeypatch.setenv("CODECRAFT_MODEL", "model-a")
    monkeypatch.setenv("APINEX_API_KEY", "apinex-key")
    monkeypatch.setenv("APINEX_MODEL", "model-b")

    class FakeClient:
        def __init__(self, **kwargs):
            self.base_url = kwargs["base_url"]
            if self.base_url == "https://codecraftapi.com/v1":
                self.chat = SimpleNamespace(
                    completions=SimpleNamespace(
                        create=lambda **kwargs: (_ for _ in ()).throw(TimeoutError())
                    )
                )
            else:
                self.chat = SimpleNamespace(
                    completions=SimpleNamespace(
                        create=lambda **kwargs: _response("Reviewed script")
                    )
                )

    monkeypatch.setattr(router, "OpenAI", FakeClient)
    result = router.generate_text(
        task="script_review",
        system_prompt="Review factual accuracy.",
        user_prompt="A sample script.",
        provider_order=("codecraft", "apinex"),
    )

    assert result.provider == "apinex"
    assert result.content == "Reviewed script"


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        (
            {
                "task": "publish_video",
                "system_prompt": "Do it",
                "user_prompt": "Do it",
            },
            "Unsupported intelligence task",
        ),
        (
            {
                "task": "script_draft",
                "system_prompt": "",
                "user_prompt": "Topic",
            },
            "must be non-empty",
        ),
        (
            {
                "task": "script_draft",
                "system_prompt": "System",
                "user_prompt": "Topic",
                "max_output_tokens": 2001,
            },
            "max_output_tokens",
        ),
    ],
)
def test_generate_text_rejects_invalid_requests(kwargs, message):
    with pytest.raises(ValueError, match=message):
        router.generate_text(**kwargs)


def test_generate_text_reports_missing_configuration(monkeypatch):
    monkeypatch.delenv("CODECRAFT_API_KEY", raising=False)
    monkeypatch.delenv("CODECRAFT_MODEL", raising=False)
    monkeypatch.delenv("APINEX_API_KEY", raising=False)
    monkeypatch.delenv("APINEX_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    with pytest.raises(router.IntelligenceRouterError, match="No intelligence provider"):
        router.generate_text(
            task="topic_score",
            system_prompt="Score a topic.",
            user_prompt="Why AI automation matters.",
        )
