from types import SimpleNamespace

import pytest

from app.services import intelligence_router as router


def _response(content: str):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(prompt_tokens=12, completion_tokens=7),
    )


def test_generate_text_uses_configured_provider_and_reports_sent_token_cap(monkeypatch):
    monkeypatch.setenv("CODECRAFT_API_KEY", "test-key")
    monkeypatch.setenv("CODECRAFT_MODEL", "test-model")
    request_args = {}

    class FakeClient:
        def __init__(self, **kwargs):
            assert kwargs["base_url"] == "https://codecraftapi.com/v1"
            assert kwargs["max_retries"] == 0
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **kwargs: (
                        request_args.update(kwargs) or _response("  Draft script  ")
                    )
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
    # CodeCraft promotes max_tokens values below 2048, so be explicit and honest.
    assert request_args["max_tokens"] == 2048
    assert "temperature" not in request_args
    assert result.output_token_limit_sent == 2048


def test_generate_text_falls_back_after_provider_error(monkeypatch):
    monkeypatch.setenv("CODECRAFT_API_KEY", "codecraft-key")
    monkeypatch.setenv("CODECRAFT_MODEL", "model-a")
    monkeypatch.setenv("APINEX_API_KEY", "apinex-key")
    monkeypatch.setenv("APINEX_MODEL", "model-b")
    requests_seen = []

    class FakeClient:
        def __init__(self, **kwargs):
            self.base_url = kwargs["base_url"]

        @property
        def chat(self):
            def create(**kwargs):
                assert "temperature" not in kwargs
                requests_seen.append((self.base_url, kwargs["max_tokens"]))
                if self.base_url == "https://codecraftapi.com/v1":
                    raise TimeoutError()
                return _response("Reviewed script")

            return SimpleNamespace(completions=SimpleNamespace(create=create))

    monkeypatch.setattr(router, "OpenAI", FakeClient)
    result = router.generate_text(
        task="script_review",
        system_prompt="Review factual accuracy.",
        user_prompt="A sample script.",
        provider_order=("codecraft", "apinex"),
    )

    assert result.provider == "apinex"
    assert result.content == "Reviewed script"
    assert requests_seen == [
        ("https://codecraftapi.com/v1", 2048),
        ("https://api.apinex.bond/v1", 1200),
    ]
    assert result.output_token_limit_sent == 1200


def test_apinex_respects_a_lower_requested_token_cap(monkeypatch):
    monkeypatch.setenv("APINEX_API_KEY", "apinex-key")
    monkeypatch.setenv("APINEX_MODEL", "model-b")
    request_args = {}

    class FakeClient:
        def __init__(self, **kwargs):
            assert kwargs["base_url"] == "https://api.apinex.bond/v1"
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **kwargs: (
                        request_args.update(kwargs) or _response("Reviewed script")
                    )
                )
            )

    monkeypatch.setattr(router, "OpenAI", FakeClient)
    result = router.generate_text(
        task="script_review",
        system_prompt="Review factual accuracy.",
        user_prompt="A sample script.",
        max_output_tokens=700,
        provider_order=("apinex",),
    )

    assert request_args["max_tokens"] == 700
    assert result.output_token_limit_sent == 700


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
            "non-empty strings",
        ),
        (
            {
                "task": "script_draft",
                "system_prompt": None,
                "user_prompt": "Topic",
            },
            "non-empty strings",
        ),
        (
            {
                "task": "script_draft",
                "system_prompt": "System",
                "user_prompt": "Topic",
                "max_output_tokens": 2049,
            },
            "max_output_tokens",
        ),
        (
            {
                "task": "script_draft",
                "system_prompt": "System",
                "user_prompt": "Topic",
                "max_output_tokens": True,
            },
            "max_output_tokens",
        ),
    ],
)
def test_generate_text_rejects_invalid_requests(kwargs, message):
    with pytest.raises(ValueError, match=message):
        router.generate_text(**kwargs)


def test_generate_text_rejects_oversized_prompts():
    with pytest.raises(ValueError, match="Combined prompt exceeds"):
        router.generate_text(
            task="script_draft",
            system_prompt="a" * router.MAX_PROMPT_CHARS,
            user_prompt="b",
        )




def test_openai_uses_modern_completion_token_parameter(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("OPENAI_MODEL", "reasoning-model")
    request_args = {}

    class FakeClient:
        def __init__(self, **kwargs):
            assert kwargs["base_url"] == "https://api.openai.com/v1"
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **kwargs: (
                        request_args.update(kwargs) or _response("OpenAI script")
                    )
                )
            )

    monkeypatch.setattr(router, "OpenAI", FakeClient)
    result = router.generate_text(
        task="script_draft",
        system_prompt="Write a short script.",
        user_prompt="Explain a safe workflow.",
        max_output_tokens=800,
        provider_order=("openai",),
    )

    assert request_args["max_completion_tokens"] == 800
    assert "max_tokens" not in request_args
    assert "temperature" not in request_args
    assert result.output_token_limit_sent == 800
    assert result.provider == "openai"

def test_generate_text_reports_missing_configuration(monkeypatch):
    for name in (
        "CODECRAFT_API_KEY",
        "CODECRAFT_MODEL",
        "APINEX_API_KEY",
        "APINEX_MODEL",
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(router.IntelligenceRouterError, match="No intelligence provider"):
        router.generate_text(
            task="topic_score",
            system_prompt="Score a topic.",
            user_prompt="Why AI automation matters.",
        )


def test_generate_text_rejects_unknown_provider_order():
    with pytest.raises(ValueError, match="Unknown intelligence provider"):
        router.generate_text(
            task="topic_score",
            system_prompt="Score a topic.",
            user_prompt="AI automation",
            provider_order=("unknown-provider",),
        )
