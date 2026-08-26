import pytest
from pydantic import ValidationError

from app.schemas import FeedCreate
from app.validation import validate_proxy_url


def test_proxy_validator_rejects_embedded_credentials() -> None:
    with pytest.raises(ValueError, match="must not include credentials"):
        validate_proxy_url("http://user:password@proxy.example:8080")

    with pytest.raises(ValidationError, match="must not include credentials"):
        FeedCreate(name="Feed", url="https://example.test/rss", proxy_url="socks5://user@proxy.example:1080")


def test_feed_schema_rejects_unknown_adapter_type() -> None:
    with pytest.raises(ValidationError):
        FeedCreate(name="Feed", url="https://example.test/rss", adapter_type="unsupported")

    feed = FeedCreate(name="Feed", url="https://example.test/rss", adapter_type="torrentleech")
    assert feed.adapter_type == "torrentleech"
