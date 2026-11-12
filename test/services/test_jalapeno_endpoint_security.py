"""Security checks for provider URLs that receive Bearer API credentials."""

import pytest

from app.services import jalapeno_video as provider


def _settings(base_url: str) -> dict:
    return {
        "jalapeno_video_api_key": "test-only-secret",
        "jalapeno_video_base_url": base_url,
    }


@pytest.mark.parametrize(
    "base_url",
    [
        "http://api.example.test/api/v3",
        "http://192.0.2.10/api/v3",
        "http://[2001:db8::1]/api/v3",
    ],
)
def test_remote_http_video_endpoint_is_rejected(base_url):
    with pytest.raises(provider.JalapenoVideoError, match="HTTPS"):
        provider.endpoint(_settings(base_url))


@pytest.mark.parametrize(
    "base_url",
    [
        "http://localhost:8080/api/v3",
        "http://127.0.0.1:8080/api/v3",
        "http://[::1]:8080/api/v3",
    ],
)
def test_loopback_http_is_allowed_for_local_development(base_url):
    result = provider.endpoint(_settings(base_url))
    assert result.tasks_url == base_url.rstrip("/") + provider.TASKS_PATH
    assert "test-only-secret" not in repr(result)


def test_https_remote_video_endpoint_is_allowed():
    base_url = "https://api.example.test/api/v3"
    result = provider.endpoint(_settings(base_url))
    assert result.tasks_url == base_url + provider.TASKS_PATH
