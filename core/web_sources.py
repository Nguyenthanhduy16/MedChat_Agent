from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx


class DomainNotAllowedError(ValueError):
    pass


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


def _trust_tier(host: str) -> str:
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
    def __init__(self, whitelist_domains: list[str]) -> None:
        self.whitelist_domains = whitelist_domains

    async def fetch_url(
        self, url: str, timeout_seconds: float
    ) -> WebFetchedSource:
        enforce_allowed_url(url, self.whitelist_domains)

        async with httpx.AsyncClient(
            timeout=timeout_seconds, follow_redirects=True
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

        final_url = str(response.url)
        final_host = enforce_allowed_url(final_url, self.whitelist_domains)
        parser = _HTMLTextParser()
        parser.feed(response.text)

        title = parser.title or final_host
        text = parser.text[:2000]

        return WebFetchedSource(
            title=title,
            url=final_url,
            source=final_host,
            text=text,
            trust_tier=_trust_tier(final_host),
        )
