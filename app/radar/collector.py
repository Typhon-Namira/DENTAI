from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import re
import socket
from dataclasses import dataclass
from datetime import UTC, datetime
from html import unescape
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings


class RadarCollectorError(RuntimeError):
    def __init__(self, code: str, message: str, *, retryable: bool = True):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


@dataclass(frozen=True)
class CollectedSignal:
    external_signal_id: str | None
    signal_type: str
    text: str
    context_text: str | None
    source_url: str
    author_external_id: str | None
    author_display: str | None
    author_profile_url: str | None
    observed_at: datetime
    published_at: datetime | None


@dataclass(frozen=True)
class CollectorResult:
    signals: list[CollectedSignal]
    discovered_sources: list[dict[str, Any]]
    collector: str
    fetched_at: datetime
    source_revision: str | None = None


class _TextBlockParser(HTMLParser):
    BLOCK_TAGS = {"article", "p", "li", "blockquote", "h1", "h2", "h3", "h4"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._tag: str | None = None
        self._buffer: list[str] = []
        self.blocks: list[str] = []
        self.title = ""
        self._in_title = False
        self._title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "title":
            self._in_title = True
        if tag in self.BLOCK_TAGS:
            self._flush()
            self._tag = tag

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
            self.title = _clean_text(" ".join(self._title_parts))
        if self._tag == tag:
            self._flush()
            self._tag = None

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)
        if self._tag:
            self._buffer.append(data)

    def _flush(self) -> None:
        if not self._buffer:
            return
        text = _clean_text(" ".join(self._buffer))
        self._buffer.clear()
        if len(text) >= 18:
            self.blocks.append(text)


class _TelegramParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.current_post: str | None = None
        self.current_url: str | None = None
        self.current_author: str | None = None
        self.current_datetime: datetime | None = None
        self._capture_text = False
        self._capture_author = False
        self._parts: list[str] = []
        self.messages: list[CollectedSignal] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = (values.get("class") or "").split()
        if tag == "div" and "tgme_widget_message" in classes:
            self._flush_message()
            self.current_post = values.get("data-post")
            if self.current_post:
                self.current_url = f"https://t.me/{self.current_post}"
        elif tag == "div" and "tgme_widget_message_text" in classes:
            self._capture_text = True
        elif tag in {"a", "span"} and "tgme_widget_message_owner_name" in classes:
            self._capture_author = True
        elif tag == "time" and values.get("datetime"):
            try:
                parsed = datetime.fromisoformat(values["datetime"].replace("Z", "+00:00"))
                self.current_datetime = parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
            except ValueError:
                self.current_datetime = None
        elif self._capture_text and tag == "br":
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag == "div" and self._capture_text:
            self._capture_text = False
        if tag in {"a", "span"} and self._capture_author:
            self._capture_author = False

    def handle_data(self, data: str) -> None:
        if self._capture_text:
            self._parts.append(data)
        elif self._capture_author and not self.current_author:
            value = _clean_text(data)
            if value:
                self.current_author = value

    def close(self) -> None:
        super().close()
        self._flush_message()

    def _flush_message(self) -> None:
        text = _clean_text(" ".join(self._parts))
        if text:
            post_id = self.current_post or hashlib.sha256(text.encode()).hexdigest()[:24]
            self.messages.append(
                CollectedSignal(
                    external_signal_id=post_id,
                    signal_type="MESSAGE",
                    text=text,
                    context_text=None,
                    source_url=self.current_url or self.base_url,
                    author_external_id=self.current_author,
                    author_display=self.current_author,
                    author_profile_url=None,
                    observed_at=datetime.now(UTC),
                    published_at=self.current_datetime,
                )
            )
        self.current_post = None
        self.current_url = None
        self.current_author = None
        self.current_datetime = None
        self._parts = []


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if href and href.startswith(("http://", "https://")):
            self.links.append(href)


def discover_public_links(html: str) -> list[dict[str, Any]]:
    parser = _LinkParser()
    parser.feed(html)
    parser.close()
    discovered: list[dict[str, Any]] = []
    seen: set[str] = set()
    for href in parser.links:
        parsed = urlparse(href)
        host = (parsed.hostname or "").casefold().removeprefix("www.")
        platform = None
        source_type = "WEB_SOURCE"
        if host in {"instagram.com"}:
            platform, source_type = "INSTAGRAM", "PROFILE"
        elif host in {"facebook.com", "m.facebook.com"}:
            platform, source_type = "FACEBOOK", "PAGE"
        elif host in {"t.me", "telegram.me"}:
            platform, source_type = "TELEGRAM", "CHANNEL"
        elif parsed.scheme in {"http", "https"}:
            platform = "WEB"
        if not platform or href in seen:
            continue
        seen.add(href)
        discovered.append({"platform": platform, "source_type": source_type, "source_url": href})
        if len(discovered) >= 50:
            break
    return discovered


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(value or "")).strip()


def _stable_signal_id(source_url: str, text: str) -> str:
    return hashlib.sha256(f"{source_url}\n{text}".encode("utf-8")).hexdigest()


def _is_public_ip(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )


async def validate_external_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise RadarCollectorError(
            "RADAR_SOURCE_URL_INVALID",
            "Only HTTP(S) source URLs are allowed.",
            retryable=False,
        )
    if parsed.username or parsed.password:
        raise RadarCollectorError(
            "RADAR_SOURCE_URL_INVALID",
            "Credentials in source URLs are not allowed.",
            retryable=False,
        )

    hostname = parsed.hostname.casefold()
    if hostname in {"localhost", "localhost.localdomain"}:
        raise RadarCollectorError(
            "RADAR_SOURCE_URL_PRIVATE",
            "Private source hosts are not allowed.",
            retryable=False,
        )

    try:
        literal = ipaddress.ip_address(hostname)
    except ValueError:
        literal = None
    if literal is not None and not _is_public_ip(str(literal)):
        raise RadarCollectorError(
            "RADAR_SOURCE_URL_PRIVATE",
            "Private source hosts are not allowed.",
            retryable=False,
        )

    def resolve() -> list[str]:
        return list(
            {
                item[4][0]
                for item in socket.getaddrinfo(
                    hostname,
                    parsed.port or 443,
                    type=socket.SOCK_STREAM,
                )
            }
        )

    try:
        addresses = await asyncio.to_thread(resolve)
    except OSError as exc:
        raise RadarCollectorError(
            "RADAR_SOURCE_DNS_FAILED",
            "Source host could not be resolved.",
        ) from exc
    if not addresses or any(not _is_public_ip(address) for address in addresses):
        raise RadarCollectorError(
            "RADAR_SOURCE_URL_PRIVATE",
            "Private source hosts are not allowed.",
            retryable=False,
        )


async def _fetch_text(url: str) -> tuple[str, str | None]:
    await validate_external_url(url)
    settings = get_settings()
    headers = {
        "User-Agent": settings.radar_user_agent,
        "Accept": "text/html,application/xhtml+xml;q=0.9,text/plain;q=0.8,*/*;q=0.5",
    }
    try:
        async with httpx.AsyncClient(
            timeout=settings.radar_http_timeout_seconds,
            follow_redirects=True,
            headers=headers,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            final_url = str(response.url)
            await validate_external_url(final_url)
            raw = response.content
    except httpx.TimeoutException as exc:
        raise RadarCollectorError("RADAR_SOURCE_TIMEOUT", "Source request timed out.") from exc
    except httpx.HTTPStatusError as exc:
        retryable = exc.response.status_code >= 500 or exc.response.status_code in {408, 429}
        raise RadarCollectorError(
            "RADAR_SOURCE_HTTP_ERROR",
            f"Source returned HTTP {exc.response.status_code}.",
            retryable=retryable,
        ) from exc
    except httpx.HTTPError as exc:
        raise RadarCollectorError("RADAR_SOURCE_NETWORK_ERROR", "Source request failed.") from exc

    if len(raw) > settings.radar_http_max_bytes:
        raise RadarCollectorError(
            "RADAR_SOURCE_TOO_LARGE",
            "Source response exceeded the Radar size limit.",
            retryable=False,
        )
    content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type and content_type not in {
        "text/html",
        "application/xhtml+xml",
        "text/plain",
    }:
        raise RadarCollectorError(
            "RADAR_SOURCE_CONTENT_TYPE",
            "Source did not return readable text content.",
            retryable=False,
        )
    return response.text, response.headers.get("etag") or response.headers.get("last-modified")


def parse_web_document(html: str, source_url: str, *, max_items: int) -> list[CollectedSignal]:
    parser = _TextBlockParser()
    parser.feed(html)
    parser.close()
    seen: set[str] = set()
    signals: list[CollectedSignal] = []
    context = parser.title or None
    now = datetime.now(UTC)
    for block in parser.blocks:
        normalized = _clean_text(block)
        if len(normalized) < 18:
            continue
        key = _stable_signal_id(source_url, normalized)
        if key in seen:
            continue
        seen.add(key)
        signals.append(
            CollectedSignal(
                external_signal_id=key,
                signal_type="WEB_TEXT",
                text=normalized[:20_000],
                context_text=context,
                source_url=source_url,
                author_external_id=None,
                author_display=None,
                author_profile_url=None,
                observed_at=now,
                published_at=None,
            )
        )
        if len(signals) >= max_items:
            break
    return signals


def parse_public_telegram(html: str, source_url: str, *, max_items: int) -> list[CollectedSignal]:
    parser = _TelegramParser(source_url)
    parser.feed(html)
    parser.close()
    deduped: list[CollectedSignal] = []
    seen: set[str] = set()
    for item in parser.messages:
        key = item.external_signal_id or _stable_signal_id(item.source_url, item.text)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
        if len(deduped) >= max_items:
            break
    return deduped


async def collect_builtin(platform: str, source_url: str) -> CollectorResult:
    settings = get_settings()
    platform = platform.strip().upper()
    fetch_url = source_url
    if platform == "TELEGRAM":
        parsed = urlparse(source_url)
        path = parsed.path.strip("/")
        if (
            parsed.hostname
            and parsed.hostname.casefold() in {"t.me", "telegram.me"}
            and path
            and not path.startswith("s/")
        ):
            fetch_url = f"https://t.me/s/{path.split('/', 1)[0]}"
    elif platform != "WEB":
        raise RadarCollectorError(
            "RADAR_AUTH_SESSION_REQUIRED",
            f"{platform.title()} requires the authorized session collector.",
            retryable=False,
        )

    html, revision = await _fetch_text(fetch_url)
    if platform == "TELEGRAM":
        signals = parse_public_telegram(
            html,
            source_url,
            max_items=settings.radar_max_items_per_poll,
        )
    else:
        signals = parse_web_document(
            html,
            source_url,
            max_items=settings.radar_max_items_per_poll,
        )
    return CollectorResult(
        signals=signals,
        discovered_sources=discover_public_links(html),
        collector="builtin",
        fetched_at=datetime.now(UTC),
        source_revision=revision,
    )


async def collect_remote(*, clinic_id: str, source: Any) -> CollectorResult:
    settings = get_settings()
    if not settings.radar_collector_url:
        raise RadarCollectorError(
            "RADAR_AUTH_SESSION_REQUIRED",
            f"{source.platform.title()} requires the authorized session collector.",
            retryable=False,
        )
    headers: dict[str, str] = {}
    if settings.radar_collector_token:
        headers["Authorization"] = f"Bearer {settings.radar_collector_token}"
    payload = {
        "clinic_id": clinic_id,
        "source": {
            "id": str(source.id),
            "platform": source.platform,
            "external_source_id": source.external_source_id,
            "source_type": source.source_type,
            "name": source.name,
            "handle": source.handle,
            "source_url": source.source_url,
            "metadata": source.source_metadata or {},
        },
        "limits": {"max_items": settings.radar_max_items_per_poll},
        "mode": "read_only",
    }
    try:
        async with httpx.AsyncClient(timeout=settings.radar_collector_timeout_seconds) as client:
            response = await client.post(
                settings.radar_collector_url.rstrip("/") + "/v1/collect",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException as exc:
        raise RadarCollectorError(
            "RADAR_COLLECTOR_TIMEOUT",
            "Authorized collector timed out.",
        ) from exc
    except httpx.HTTPStatusError as exc:
        retryable = exc.response.status_code >= 500 or exc.response.status_code in {408, 429}
        code = (
            "RADAR_AUTH_SESSION_REQUIRED"
            if exc.response.status_code in {401, 403, 409}
            else "RADAR_COLLECTOR_HTTP_ERROR"
        )
        raise RadarCollectorError(
            code,
            "Authorized collector rejected the source.",
            retryable=retryable,
        ) from exc
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        raise RadarCollectorError(
            "RADAR_COLLECTOR_INVALID_RESPONSE",
            "Authorized collector response was invalid.",
        ) from exc

    signals: list[CollectedSignal] = []
    now = datetime.now(UTC)
    for raw in list(data.get("signals") or [])[: settings.radar_max_items_per_poll]:
        text = _clean_text(str(raw.get("text") or ""))
        source_url = str(raw.get("source_url") or source.source_url)
        if not text:
            continue
        published_at = None
        if raw.get("published_at"):
            try:
                published_at = datetime.fromisoformat(str(raw["published_at"]).replace("Z", "+00:00"))
            except ValueError:
                published_at = None
        signals.append(
            CollectedSignal(
                external_signal_id=(
                    str(raw.get("external_signal_id")) if raw.get("external_signal_id") else None
                ),
                signal_type=str(raw.get("signal_type") or "COMMENT").upper(),
                text=text[:20_000],
                context_text=_clean_text(str(raw.get("context_text") or ""))[:30_000] or None,
                source_url=source_url,
                author_external_id=(
                    str(raw.get("author_external_id")) if raw.get("author_external_id") else None
                ),
                author_display=_clean_text(str(raw.get("author_display") or ""))[:300] or None,
                author_profile_url=(
                    str(raw.get("author_profile_url")) if raw.get("author_profile_url") else None
                ),
                observed_at=now,
                published_at=published_at,
            )
        )
    return CollectorResult(
        signals=signals,
        discovered_sources=list(data.get("discovered_sources") or [])[:100],
        collector="remote",
        fetched_at=now,
        source_revision=str(data.get("source_revision")) if data.get("source_revision") else None,
    )


async def collect_source(*, clinic_id: str, source: Any) -> CollectorResult:
    platform = source.platform.strip().upper()
    metadata = source.source_metadata or {}
    if metadata.get("collector") == "remote" or platform in {"INSTAGRAM", "FACEBOOK"}:
        return await collect_remote(clinic_id=clinic_id, source=source)
    try:
        return await collect_builtin(platform, source.source_url)
    except RadarCollectorError as exc:
        if exc.code == "RADAR_AUTH_SESSION_REQUIRED" and get_settings().radar_collector_url:
            return await collect_remote(clinic_id=clinic_id, source=source)
        raise


async def collector_runtime_status() -> dict[str, Any]:
    settings = get_settings()
    remote = {
        "configured": bool(settings.radar_collector_url),
        "reachable": False,
        "detail": "Not configured",
    }
    if settings.radar_collector_url:
        headers: dict[str, str] = {}
        if settings.radar_collector_token:
            headers["Authorization"] = f"Bearer {settings.radar_collector_token}"
        try:
            async with httpx.AsyncClient(
                timeout=min(settings.radar_collector_timeout_seconds, 5)
            ) as client:
                response = await client.get(
                    settings.radar_collector_url.rstrip("/") + "/health",
                    headers=headers,
                )
                response.raise_for_status()
            remote.update(reachable=True, detail="Authorized collector online")
        except httpx.HTTPError:
            remote["detail"] = "Configured but unreachable"
    return {
        "WEB": {"ready": True, "mode": "builtin", "detail": "Public web collector ready"},
        "TELEGRAM": {
            "ready": True,
            "mode": "builtin+remote" if remote["configured"] else "builtin",
            "detail": "Public Telegram ready; protected sources use authorized collector",
        },
        "INSTAGRAM": {
            "ready": bool(remote["configured"] and remote["reachable"]),
            "mode": "authorized_session",
            "detail": remote["detail"],
        },
        "FACEBOOK": {
            "ready": bool(remote["configured"] and remote["reachable"]),
            "mode": "authorized_session",
            "detail": remote["detail"],
        },
        "remote": remote,
    }
