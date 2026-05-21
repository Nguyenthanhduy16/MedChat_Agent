from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any, Protocol
from urllib.parse import urlparse

import httpx

from core.models import RetrievalPlan


class DomainNotAllowedError(ValueError):
    pass


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str


class WebSearchProvider(Protocol):
    async def search(self, query: str, timeout_seconds: float) -> list[SearchResult]:
        raise NotImplementedError


class HTTPJSONSearchProvider:
    def __init__(self, endpoint: str, api_key: str | None = None) -> None:
        self.endpoint = endpoint
        self.api_key = api_key

    async def search(self, query: str, timeout_seconds: float) -> list[SearchResult]:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.get(
                self.endpoint,
                params={"q": query},
                headers=headers,
            )
            response.raise_for_status()

        payload = response.json()
        raw_results = _extract_search_results(payload)
        results: list[SearchResult] = []
        for raw in raw_results:
            if not isinstance(raw, dict):
                continue
            url = _first_string(raw, ("url", "link", "href"))
            if not url:
                continue
            results.append(
                SearchResult(
                    title=_first_string(raw, ("title", "name")) or url,
                    url=url,
                    snippet=_first_string(raw, ("snippet", "description", "text")) or "",
                )
            )
        return results


class TavilySearchProvider:
    def __init__(self, endpoint: str, api_key: str, max_results: int = 10) -> None:
        self.endpoint = endpoint
        self.api_key = api_key
        self.max_results = max_results

    async def search(self, query: str, timeout_seconds: float) -> list[SearchResult]:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(
                self.endpoint,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "query": query,
                    "search_depth": "basic",
                    "include_answer": False,
                    "include_raw_content": False,
                    "max_results": self.max_results,
                },
            )
            response.raise_for_status()

        payload = response.json()
        raw_results = _extract_search_results(payload)
        results: list[SearchResult] = []
        for raw in raw_results:
            if not isinstance(raw, dict):
                continue
            url = _first_string(raw, ("url", "link", "href"))
            if not url:
                continue
            results.append(
                SearchResult(
                    title=_first_string(raw, ("title", "name")) or url,
                    url=url,
                    snippet=_first_string(raw, ("content", "snippet", "description", "text")) or "",
                )
            )
        return results


@dataclass(frozen=True)
class WebFetchedSource:
    title: str
    url: str
    source: str
    text: str
    trust_tier: str


class _HTMLTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title_parts: list[str] = []
        self.body_parts: list[str] = []
        self._in_title = False
        self._in_body = False
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "title":
            self._in_title = True
        elif tag == "body":
            self._in_body = True
        elif self._in_body and tag in {"script", "style", "noscript"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
        elif tag == "body":
            self._in_body = False
        elif self._skip_depth and tag in {"script", "style", "noscript"}:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        value = data.strip()
        if not value:
            return

        if self._in_title:
            self.title_parts.append(value)
        elif self._in_body and not self._skip_depth:
            self.body_parts.append(value)

    @property
    def title(self) -> str:
        return " ".join(self.title_parts).strip()

    @property
    def text(self) -> str:
        return " ".join(self.body_parts).strip()


def build_domain_query(domain: str, query: str) -> str:
    return f"site:{domain.strip()} {query.strip()}"


def _extract_search_results(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ("results", "items", "organic_results", "web", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            nested = _extract_search_results(value)
            if nested:
                return nested
    return []


def _first_string(payload: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def enforce_allowed_url(url: str, whitelist_domains: list[str]) -> str:
    parsed = urlparse(url)
    host = parsed.hostname
    if not host:
        raise DomainNotAllowedError(f"URL host is not allowed: {url}")

    normalized_host = host.lower().rstrip(".")
    normalized_domains = [
        domain.lower().strip().rstrip(".")
        for domain in whitelist_domains
        if domain.strip()
    ]

    for domain in normalized_domains:
        if normalized_host == domain or normalized_host.endswith(f".{domain}"):
            return normalized_host

    raise DomainNotAllowedError(f"URL host is not allowed: {url}")


def _trust_tier(host: str, web_mode: str = "trusted") -> str:
    if web_mode == "open":
        return "web_open"
    normalized_host = host.lower().rstrip(".")
    regulatory_domains = {
        "fda.gov",
        "dailymed.nlm.nih.gov",
        "ema.europa.eu",
        "moh.gov.vn",
    }
    clinical_reference_domains = {
        "who.int",
        "pubmed.ncbi.nlm.nih.gov",
        "medicines.org.uk",
    }

    if any(normalized_host == domain or normalized_host.endswith(f".{domain}") for domain in regulatory_domains):
        return "regulatory"
    if any(
        normalized_host == domain or normalized_host.endswith(f".{domain}") for domain in clinical_reference_domains
    ):
        return "clinical_reference"
    return "web_whitelisted"


class WebSourceClient:
    def __init__(
        self,
        whitelist_domains: list[str],
        search_provider: WebSearchProvider | None = None,
    ) -> None:
        self.whitelist_domains = whitelist_domains
        self.search_provider = search_provider

    async def fetch_url(
        self, url: str, timeout_seconds: float, web_mode: str = "trusted"
    ) -> WebFetchedSource:
        if web_mode != "open":
            enforce_allowed_url(url, self.whitelist_domains)

        async with httpx.AsyncClient(
            timeout=timeout_seconds, follow_redirects=True
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

        final_url = str(response.url)
        final_host = (
            _url_host(final_url)
            if web_mode == "open"
            else enforce_allowed_url(final_url, self.whitelist_domains)
        )
        parser = _HTMLTextParser()
        parser.feed(response.text)

        title = parser.title or final_host
        text = parser.text[:2000]

        return WebFetchedSource(
            title=title,
            url=final_url,
            source=final_host,
            text=text,
            trust_tier=_trust_tier(final_host, web_mode=web_mode),
        )

    async def retrieve(
        self,
        plan: RetrievalPlan,
        query_text: str,
        timeout_seconds: float,
        max_sources: int,
        web_mode: str = "trusted",
    ) -> list[WebFetchedSource]:
        if self.search_provider is None or max_sources <= 0:
            return []

        sources: list[WebFetchedSource] = []
        seen_urls: set[str] = set()
        base_query = query_text.strip() or " ".join(plan.queries).strip()
        if web_mode == "open":
            return await self._retrieve_open(base_query, timeout_seconds, max_sources)

        for domain in _domains_for_plan(self.whitelist_domains, plan):
            if len(sources) >= max_sources:
                break
            try:
                results = await self.search_provider.search(
                    build_domain_query(domain, base_query),
                    timeout_seconds=timeout_seconds,
                )
            except Exception:
                continue

            for result in results:
                if len(sources) >= max_sources:
                    break
                try:
                    enforce_allowed_url(result.url, self.whitelist_domains)
                except DomainNotAllowedError:
                    continue
                if result.url in seen_urls:
                    continue

                try:
                    source = await self.fetch_url(result.url, timeout_seconds=timeout_seconds)
                except Exception:
                    continue

                seen_urls.add(source.url)
                sources.append(source)

        return sources

    async def _retrieve_open(
        self,
        query_text: str,
        timeout_seconds: float,
        max_sources: int,
    ) -> list[WebFetchedSource]:
        sources: list[WebFetchedSource] = []
        seen_urls: set[str] = set()
        try:
            results = await self.search_provider.search(query_text, timeout_seconds=timeout_seconds)
        except Exception:
            return []

        for result in results:
            if len(sources) >= max_sources:
                break
            if result.url in seen_urls or _is_blocked_open_url(result.url):
                continue
            try:
                source = await self.fetch_url(result.url, timeout_seconds=timeout_seconds, web_mode="open")
            except Exception:
                continue
            seen_urls.add(source.url)
            sources.append(source)
        return sources


def _url_host(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.hostname
    if not host:
        raise DomainNotAllowedError(f"URL host is not allowed: {url}")
    return host.lower().rstrip(".")


def _is_blocked_open_url(url: str) -> bool:
    try:
        host = _url_host(url)
    except DomainNotAllowedError:
        return True
    blocked_domains = (
        "facebook.com",
        "instagram.com",
        "tiktok.com",
        "twitter.com",
        "x.com",
        "youtube.com",
    )
    return any(host == domain or host.endswith(f".{domain}") for domain in blocked_domains)


def _domains_for_plan(whitelist_domains: list[str], plan: RetrievalPlan) -> list[str]:
    domains = [
        domain.lower().strip().rstrip(".")
        for domain in whitelist_domains
        if domain.strip()
    ]
    return list(dict.fromkeys(domains))
