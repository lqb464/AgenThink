"""
Free research browsing tools.

Primary: SearXNG self-hosted JSON API (SEARXNG_URL).
Also: Wikipedia MediaWiki API, arXiv Atom API.
Optional: DuckDuckGo HTML scrape (ENABLE_DDG_FALLBACK) — rate-limited, not primary.
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from html import unescape
from urllib.parse import quote

import httpx

from backend.core.config import settings
from backend.core.rate_limit import RateLimiter

logger = logging.getLogger(__name__)

_search_limiter = RateLimiter(
    max_calls=getattr(settings, "SEARCH_RATE_LIMIT_MAX_CALLS", 20),
    time_window_seconds=getattr(settings, "SEARCH_RATE_LIMIT_WINDOW_SECONDS", 60.0),
)

_USER_AGENT = "AgenThink/0.3 (research; educational; +https://localhost)"
_HTTP_TIMEOUT = 12.0

_ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _rate_limited(bucket: str) -> str | None:
    if not _search_limiter.allow(bucket):
        return (
            f"[Rate limited] Too many {bucket} requests. "
            "Wait a moment and try again with a narrower query."
        )
    return None


def _format_results(title: str, results: list[dict[str, str]], *, empty_msg: str) -> str:
    if not results:
        return empty_msg
    lines = [title]
    for i, item in enumerate(results, start=1):
        name = item.get("title") or "(untitled)"
        url = item.get("url") or ""
        snippet = (item.get("snippet") or "").strip()
        lines.append(f"{i}. {name}")
        if url:
            lines.append(f"   URL: {url}")
        if snippet:
            lines.append(f"   {snippet}")
    lines.append("\nCite sources by title and URL when answering.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# SearXNG (primary web search)
# ---------------------------------------------------------------------------


def check_searxng_health() -> bool:
    """Return True if SearXNG responds (optional dependency)."""
    base = (settings.SEARXNG_URL or "").rstrip("/")
    if not base:
        return False
    try:
        with httpx.Client(timeout=3.0, headers={"User-Agent": _USER_AGENT}) as client:
            # Prefer /healthz when present; fall back to a tiny JSON search probe
            for path in ("/healthz", "/"):
                try:
                    r = client.get(f"{base}{path}")
                    if r.status_code == 200:
                        return True
                except Exception:
                    continue
            r = client.get(f"{base}/search", params={"q": "ping", "format": "json"})
            return r.status_code == 200
    except Exception:
        return False


def web_search(query: str, max_results: int = 5) -> str:
    """
    Query SearXNG and return titled results + URLs for the agent to cite.
    Soft-fails with a clear message if SearXNG is down (does not raise).
    """
    q = (query or "").strip()
    if not q:
        return "[web_search] Empty query."

    limited = _rate_limited("web_search")
    if limited:
        return limited

    max_results = max(1, min(int(max_results or 5), 10))
    base = (settings.SEARXNG_URL or "").rstrip("/")
    if not base:
        return (
            "[web_search] SEARXNG_URL is not configured. "
            "With Docker Compose, SearXNG is included; set SEARXNG_URL=http://localhost:8080 for local API."
        )

    try:
        with httpx.Client(timeout=_HTTP_TIMEOUT, headers={"User-Agent": _USER_AGENT}) as client:
            response = client.get(
                f"{base}/search",
                params={"q": q, "format": "json", "language": "auto"},
            )
            response.raise_for_status()
            data = response.json()
    except httpx.ConnectError:
        fallback = _maybe_ddg_fallback(q, max_results)
        if fallback is not None:
            return fallback
        return (
            f"[web_search] Cannot connect to SearXNG at {base}. "
            "With Compose: docker compose up -d. Local API: SEARXNG_URL=http://localhost:8080. "
            "Then retry, or use wikipedia_lookup / arxiv_search."
        )
    except httpx.HTTPStatusError as exc:
        return (
            f"[web_search] SearXNG returned HTTP {exc.response.status_code}. "
            "Check that JSON format is enabled in backend/tools/web_search/settings.yml."
        )
    except Exception as exc:
        logger.warning("web_search failed: %s", exc)
        fallback = _maybe_ddg_fallback(q, max_results)
        if fallback is not None:
            return fallback
        return f"[web_search] SearXNG error: {exc}"

    raw_results = data.get("results") or []
    results: list[dict[str, str]] = []
    for item in raw_results[:max_results]:
        results.append(
            {
                "title": str(item.get("title") or "").strip(),
                "url": str(item.get("url") or "").strip(),
                "snippet": str(item.get("content") or item.get("snippet") or "").strip()[:400],
            }
        )

    if not results:
        fallback = _maybe_ddg_fallback(q, max_results)
        if fallback is not None:
            return fallback
        return f"[web_search] No results for '{q}'."

    return _format_results(
        f"Web search results for '{q}' (via SearXNG):",
        results,
        empty_msg=f"[web_search] No results for '{q}'.",
    )


# ---------------------------------------------------------------------------
# Optional DuckDuckGo HTML fallback (ToS risk — off by default)
# ---------------------------------------------------------------------------


def _maybe_ddg_fallback(query: str, max_results: int) -> str | None:
    if not getattr(settings, "ENABLE_DDG_FALLBACK", False):
        return None
    limited = _rate_limited("ddg_fallback")
    if limited:
        return limited
    try:
        return _ddg_html_search(query, max_results)
    except Exception as exc:
        logger.info("DDG fallback failed: %s", exc)
        return None


def _ddg_html_search(query: str, max_results: int) -> str:
    """Minimal HTML scrape of DuckDuckGo HTML endpoint — last-resort only."""
    url = "https://html.duckduckgo.com/html/"
    with httpx.Client(
        timeout=_HTTP_TIMEOUT,
        headers={"User-Agent": _USER_AGENT},
        follow_redirects=True,
    ) as client:
        response = client.post(url, data={"q": query})
        response.raise_for_status()
        html = response.text

    # Very small parser: result links with class result__a
    pattern = re.compile(
        r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
        flags=re.IGNORECASE | re.DOTALL,
    )
    snippet_pat = re.compile(
        r'class="result__snippet"[^>]*>(.*?)</(?:a|td|div)>',
        flags=re.IGNORECASE | re.DOTALL,
    )
    titles = pattern.findall(html)
    snippets = [re.sub(r"<[^>]+>", "", unescape(s)).strip() for s in snippet_pat.findall(html)]

    results: list[dict[str, str]] = []
    for i, (href, title_html) in enumerate(titles[:max_results]):
        title = re.sub(r"<[^>]+>", "", unescape(title_html)).strip()
        snippet = snippets[i][:400] if i < len(snippets) else ""
        results.append({"title": title, "url": href, "snippet": snippet})

    return _format_results(
        f"Web search results for '{query}' (DuckDuckGo fallback — optional):",
        results,
        empty_msg=f"[web_search/ddg] No results for '{query}'.",
    )


# ---------------------------------------------------------------------------
# Wikipedia
# ---------------------------------------------------------------------------


def wikipedia_lookup(query: str, lang: str = "en", sentences: int = 4) -> str:
    """
    Look up a Wikipedia page summary via the free MediaWiki / REST APIs.
    Soft-fails with a clear message on network errors.
    """
    q = (query or "").strip()
    if not q:
        return "[wikipedia_lookup] Empty query."

    limited = _rate_limited("wikipedia")
    if limited:
        return limited

    lang = (lang or "en").strip().lower()[:8] or "en"
    sentences = max(1, min(int(sentences or 4), 10))

    try:
        with httpx.Client(timeout=_HTTP_TIMEOUT, headers={"User-Agent": _USER_AGENT}) as client:
            # 1) Resolve title via opensearch
            search_url = f"https://{lang}.wikipedia.org/w/api.php"
            r = client.get(
                search_url,
                params={
                    "action": "opensearch",
                    "search": q,
                    "limit": 5,
                    "namespace": 0,
                    "format": "json",
                },
            )
            r.raise_for_status()
            data = r.json()
            titles = data[1] if isinstance(data, list) and len(data) > 1 else []
            urls = data[3] if isinstance(data, list) and len(data) > 3 else []
            if not titles:
                # Try English if non-en miss
                if lang != "en":
                    return wikipedia_lookup(q, lang="en", sentences=sentences)
                return f"[wikipedia_lookup] No Wikipedia page found for '{q}' (lang={lang})."

            # 2) Summary for top hit
            top_title = titles[0]
            summary_url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(top_title)}"
            s = client.get(summary_url)
            s.raise_for_status()
            summary = s.json()
    except httpx.HTTPError as exc:
        logger.warning("wikipedia_lookup failed: %s", exc)
        return f"[wikipedia_lookup] Wikipedia API error: {exc}"
    except Exception as exc:
        logger.warning("wikipedia_lookup failed: %s", exc)
        return f"[wikipedia_lookup] Error: {exc}"

    extract = (summary.get("extract") or "").strip()
    page_url = (
        (summary.get("content_urls") or {}).get("desktop", {}).get("page")
        or (urls[0] if urls else "")
        or f"https://{lang}.wikipedia.org/wiki/{quote(top_title.replace(' ', '_'))}"
    )
    display_title = summary.get("title") or top_title

    # Truncate extract roughly by sentences
    parts = re.split(r"(?<=[.!?])\s+", extract)
    short = " ".join(parts[:sentences]).strip() or extract[:600]

    related = []
    for i, t in enumerate(titles[1:5], start=2):
        u = urls[i - 1] if i - 1 < len(urls) else ""
        related.append(f"  {i}. {t}" + (f" — {u}" if u else ""))

    body = [
        f"Wikipedia ({lang}): {display_title}",
        f"URL: {page_url}",
        "",
        short,
    ]
    if related:
        body.append("")
        body.append("Related titles:")
        body.extend(related)
    body.append("\nCite the Wikipedia URL when answering.")
    return "\n".join(body)


# ---------------------------------------------------------------------------
# arXiv
# ---------------------------------------------------------------------------


def arxiv_search(query: str, max_results: int = 5) -> str:
    """Search arXiv via the free Atom API. Soft-fails on errors."""
    q = (query or "").strip()
    if not q:
        return "[arxiv_search] Empty query."

    limited = _rate_limited("arxiv")
    if limited:
        return limited

    max_results = max(1, min(int(max_results or 5), 10))
    api = "https://export.arxiv.org/api/query"
    try:
        with httpx.Client(timeout=_HTTP_TIMEOUT, headers={"User-Agent": _USER_AGENT}) as client:
            response = client.get(
                api,
                params={
                    "search_query": f"all:{q}",
                    "start": 0,
                    "max_results": max_results,
                    "sortBy": "relevance",
                    "sortOrder": "descending",
                },
            )
            response.raise_for_status()
            root = ET.fromstring(response.text)
    except httpx.HTTPError as exc:
        logger.warning("arxiv_search failed: %s", exc)
        return f"[arxiv_search] arXiv API error: {exc}"
    except ET.ParseError as exc:
        return f"[arxiv_search] Failed to parse arXiv response: {exc}"
    except Exception as exc:
        logger.warning("arxiv_search failed: %s", exc)
        return f"[arxiv_search] Error: {exc}"

    entries = root.findall("atom:entry", _ATOM_NS)
    results: list[dict[str, str]] = []
    for entry in entries[:max_results]:
        title = (entry.findtext("atom:title", default="", namespaces=_ATOM_NS) or "").strip()
        title = re.sub(r"\s+", " ", title)
        summary = (entry.findtext("atom:summary", default="", namespaces=_ATOM_NS) or "").strip()
        summary = re.sub(r"\s+", " ", summary)[:400]
        abs_url = ""
        for link in entry.findall("atom:link", _ATOM_NS):
            if link.attrib.get("rel") == "alternate" or link.attrib.get("type") == "text/html":
                abs_url = link.attrib.get("href", "")
                if abs_url:
                    break
        if not abs_url:
            abs_url = entry.findtext("atom:id", default="", namespaces=_ATOM_NS) or ""
        published = (entry.findtext("atom:published", default="", namespaces=_ATOM_NS) or "")[:10]
        authors = [
            (a.findtext("atom:name", default="", namespaces=_ATOM_NS) or "").strip()
            for a in entry.findall("atom:author", _ATOM_NS)
        ]
        author_str = ", ".join(a for a in authors[:4] if a)
        snippet_parts = []
        if published:
            snippet_parts.append(published)
        if author_str:
            snippet_parts.append(author_str)
        if summary:
            snippet_parts.append(summary)
        results.append(
            {
                "title": title,
                "url": abs_url,
                "snippet": " — ".join(snippet_parts),
            }
        )

    return _format_results(
        f"arXiv results for '{q}':",
        results,
        empty_msg=f"[arxiv_search] No papers found for '{q}'.",
    )


# ---------------------------------------------------------------------------
# Backward-compatible entry points (registry / old schemas)
# ---------------------------------------------------------------------------


def search(query: str) -> str:
    """Legacy alias — routes to SearXNG web_search."""
    return web_search(query)


def match_search(message: str) -> str | None:
    match = re.fullmatch(r"(?:Tìm|Search|Web)\s+(.+)", message.strip(), flags=re.IGNORECASE)
    if not match:
        return None
    return web_search(match.group(1).strip())
