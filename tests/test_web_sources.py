import httpx
import pytest

from core.models import RetrievalPlan, RiskLevel
from core.web_sources import (
    DomainNotAllowedError,
    HTTPJSONSearchProvider,
    SearchResult,
    TavilySearchProvider,
    WebSourceClient,
    build_domain_query,
    enforce_allowed_url,
)


def test_build_domain_scoped_query() -> None:
    query = build_domain_query("dailymed.nlm.nih.gov", "warfarin ibuprofen interaction")

    assert query == "site:dailymed.nlm.nih.gov warfarin ibuprofen interaction"


def test_enforce_allowed_url_rejects_unlisted_domain() -> None:
    with pytest.raises(DomainNotAllowedError):
        enforce_allowed_url("https://example.com/drug", ["dailymed.nlm.nih.gov"])


@pytest.mark.asyncio
async def test_http_json_search_provider_parses_common_result_shapes(respx_mock) -> None:
    route = respx_mock.get("https://search.test/api").respond(
        200,
        json={
            "results": [
                {
                    "title": "Warfarin label",
                    "url": "https://dailymed.nlm.nih.gov/warfarin",
                    "snippet": "Warfarin label text",
                }
            ]
        },
    )
    provider = HTTPJSONSearchProvider("https://search.test/api", api_key="test-key")

    results = await provider.search("site:dailymed.nlm.nih.gov warfarin", timeout_seconds=1)

    assert route.called
    assert route.calls.last.request.url.params["q"] == "site:dailymed.nlm.nih.gov warfarin"
    assert route.calls.last.request.headers["authorization"] == "Bearer test-key"
    assert results == [
        SearchResult(
            title="Warfarin label",
            url="https://dailymed.nlm.nih.gov/warfarin",
            snippet="Warfarin label text",
        )
    ]


@pytest.mark.asyncio
async def test_tavily_search_provider_posts_query_and_parses_results(respx_mock) -> None:
    route = respx_mock.post("https://api.tavily.com/search").respond(
        200,
        json={
            "results": [
                {
                    "title": "DailyMed - Abacavir",
                    "url": "https://dailymed.nlm.nih.gov/abacavir",
                    "content": "Abacavir label text",
                }
            ]
        },
    )
    provider = TavilySearchProvider("https://api.tavily.com/search", api_key="tvly-test")

    results = await provider.search("site:dailymed.nlm.nih.gov abacavir", timeout_seconds=1)

    assert route.called
    request = route.calls.last.request
    assert request.headers["authorization"] == "Bearer tvly-test"
    assert request.headers["content-type"] == "application/json"
    assert b'"query":"site:dailymed.nlm.nih.gov abacavir"' in request.content
    assert results == [
        SearchResult(
            title="DailyMed - Abacavir",
            url="https://dailymed.nlm.nih.gov/abacavir",
            snippet="Abacavir label text",
        )
    ]


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


@pytest.mark.asyncio
async def test_web_source_client_retrieves_search_results_from_whitelisted_domains(respx_mock) -> None:
    class FakeSearchProvider:
        def __init__(self) -> None:
            self.queries: list[str] = []

        async def search(self, query: str, timeout_seconds: float) -> list[SearchResult]:
            self.queries.append(query)
            return [
                SearchResult(
                    title="Warfarin",
                    url="https://dailymed.nlm.nih.gov/warfarin",
                    snippet="Warfarin label",
                ),
                SearchResult(
                    title="Not allowed",
                    url="https://example.com/warfarin",
                    snippet="Not allowed",
                ),
            ]

    route = respx_mock.get("https://dailymed.nlm.nih.gov/warfarin").respond(
        200,
        html="<html><head><title>Warfarin label</title></head><body>Warfarin label text</body></html>",
    )
    plan = RetrievalPlan(
        intents=["interaction"],
        risk_level=RiskLevel.HIGH,
        queries=["warfarin interaction"],
        entities={"drugs": ["warfarin"]},
        metadata_filters={},
    )
    search_provider = FakeSearchProvider()
    client = WebSourceClient(["dailymed.nlm.nih.gov"], search_provider=search_provider)

    items = await client.retrieve(plan, "warfarin interaction", timeout_seconds=1, max_sources=2)

    assert search_provider.queries == ["site:dailymed.nlm.nih.gov warfarin interaction"]
    assert route.called
    assert len(items) == 1
    assert items[0].url == "https://dailymed.nlm.nih.gov/warfarin"


@pytest.mark.asyncio
async def test_web_source_client_stops_after_max_sources(respx_mock) -> None:
    class FakeSearchProvider:
        async def search(self, query: str, timeout_seconds: float) -> list[SearchResult]:
            return [
                SearchResult(title="One", url="https://dailymed.nlm.nih.gov/one", snippet="one"),
                SearchResult(title="Two", url="https://dailymed.nlm.nih.gov/two", snippet="two"),
            ]

    first = respx_mock.get("https://dailymed.nlm.nih.gov/one").respond(
        200,
        html="<html><head><title>One</title></head><body>One text</body></html>",
    )
    second = respx_mock.get("https://dailymed.nlm.nih.gov/two").respond(
        200,
        html="<html><head><title>Two</title></head><body>Two text</body></html>",
    )
    plan = RetrievalPlan(
        intents=["indication"],
        risk_level=RiskLevel.LOW,
        queries=["abacavir indication"],
        entities={"drugs": ["abacavir"]},
        metadata_filters={},
    )
    client = WebSourceClient(["dailymed.nlm.nih.gov"], search_provider=FakeSearchProvider())

    items = await client.retrieve(plan, "abacavir indication", timeout_seconds=1, max_sources=1)

    assert len(items) == 1
    assert first.called
    assert not second.called


@pytest.mark.asyncio
async def test_web_source_client_skips_search_and_fetch_failures(respx_mock) -> None:
    class FakeSearchProvider:
        async def search(self, query: str, timeout_seconds: float) -> list[SearchResult]:
            return [
                SearchResult(title="Broken", url="https://dailymed.nlm.nih.gov/broken", snippet="broken"),
                SearchResult(title="Working", url="https://dailymed.nlm.nih.gov/working", snippet="working"),
            ]

    respx_mock.get("https://dailymed.nlm.nih.gov/broken").mock(side_effect=httpx.ConnectError("failed"))
    working = respx_mock.get("https://dailymed.nlm.nih.gov/working").respond(
        200,
        html="<html><head><title>Working</title></head><body>Working text</body></html>",
    )
    plan = RetrievalPlan(
        intents=["indication"],
        risk_level=RiskLevel.LOW,
        queries=["abacavir indication"],
        entities={"drugs": ["abacavir"]},
        metadata_filters={},
    )
    client = WebSourceClient(["dailymed.nlm.nih.gov"], search_provider=FakeSearchProvider())

    items = await client.retrieve(plan, "abacavir indication", timeout_seconds=1, max_sources=2)

    assert working.called
    assert [item.title for item in items] == ["Working"]
