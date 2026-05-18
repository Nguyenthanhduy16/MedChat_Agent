import pytest

from core.web_sources import DomainNotAllowedError, WebSourceClient, build_domain_query, enforce_allowed_url


def test_build_domain_scoped_query() -> None:
    query = build_domain_query("dailymed.nlm.nih.gov", "warfarin ibuprofen interaction")

    assert query == "site:dailymed.nlm.nih.gov warfarin ibuprofen interaction"


def test_enforce_allowed_url_rejects_unlisted_domain() -> None:
    with pytest.raises(DomainNotAllowedError):
        enforce_allowed_url("https://example.com/drug", ["dailymed.nlm.nih.gov"])


@pytest.mark.asyncio
async def test_web_source_client_fetches_only_whitelisted_urls(respx_mock) -> None:
    route = respx_mock.get("https://dailymed.nlm.nih.gov/drug").respond(
        200,
        html="<html><head><title>Warfarin</title></head><body>Warfarin label text</body></html>",
    )
    client = WebSourceClient(["dailymed.nlm.nih.gov"])

    item = await client.fetch_url("https://dailymed.nlm.nih.gov/drug", timeout_seconds=1)

    assert route.called
    assert item.title == "Warfarin"
    assert "Warfarin label text" in item.text
