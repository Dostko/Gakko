from __future__ import annotations

import html
import json
import re
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

from .internet_kapisi.image_arama import (
    IMAGE_SEARCH_DEFAULT_MAX_RESULTS,
    IMAGE_SEARCH_MAX_RESULTS,
    image_search_from_web_results,
)


WEB_SEARCH_URL = "https://html.duckduckgo.com/html/"
WEB_TIMEOUT_SECONDS = 60
WEB_MAX_RESPONSE_BYTES = 2_000_000
WEB_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/156.0.0.0 Safari/537.36"
)

WEB_SEARCH_DEFAULT_MAX_RESULTS = 10
WEB_SEARCH_MAX_RESULTS = 10
WEB_SEARCH_RESULT_CONTENT_MAX_CHARS = 600
WEB_SEARCH_TRANSPORT_MAX_CHARS = 12000
WEB_FETCH_CONTENT_MAX_CHARS = 24000

INTERNET_TOOL_NAMES = frozenset({"web_search", "web_fetch", "image_search"})

INTERNET_TOOLS = (
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "İnternette bir sorgu için arama sonucu getirir.",
            "parameters": {
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Arama sorgusu.",
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": WEB_SEARCH_MAX_RESULTS,
                        "description": "Döndürülecek en fazla sonuç sayısı.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Verilen URL'nin web sayfası içeriğini getirir.",
            "parameters": {
                "type": "object",
                "required": ["url"],
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "İçeriği getirilecek web adresi.",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "image_search",
            "description": (
                "İnternette sorguyla ilgili farklı web kaynaklarını arar; kaynak metinleriyle "
                "birlikte sayfaların ilan ettiği erişilebilir görselleri ve hazır Markdown satırlarını getirir. "
                "Görsel gerektiğinde kullan; konuya uygun bir markdown_image satırını final cevaba aynen ekle. "
                "Bilgi için sources alanını kullan; yetersizse web_search veya web_fetch ile doğrula."
            ),
            "parameters": {
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Aranacak görsel konusu veya kısa arama sorgusu.",
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": IMAGE_SEARCH_MAX_RESULTS,
                        "description": "Döndürülecek en fazla görsel sayısı.",
                    },
                },
            },
        },
    },
)


class _SearchParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.results = []
        self.current = None
        self.capture = None
        self.snippet_tag = None

    def _finish(self):
        if not self.current:
            return

        title = _clean_text(" ".join(self.current["title"]))
        content = _clean_text(" ".join(self.current["content"]))
        url = _clean_result_url(self.current["url"])

        if title and url:
            self.results.append(
                {"title": title, "url": url, "content": content}
            )

        self.current = None
        self.capture = None
        self.snippet_tag = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set(str(attrs.get("class", "")).split())

        if tag == "a" and "result__a" in classes:
            self._finish()
            self.current = {
                "title": [],
                "url": str(attrs.get("href", "") or ""),
                "content": [],
            }
            self.capture = "title"
        elif self.current and "result__snippet" in classes:
            self.capture = "content"
            self.snippet_tag = tag

    def handle_endtag(self, tag):
        if self.capture == "title" and tag == "a":
            self.capture = None
        elif self.capture == "content" and tag == self.snippet_tag:
            self.capture = None
            self.snippet_tag = None

    def handle_data(self, data):
        if self.current and self.capture:
            self.current[self.capture].append(data)

    def close(self):
        super().close()
        self._finish()


def _clean_text(value):
    value = re.sub(r"[ \t\r\f\v]+", " ", str(value or ""))
    value = re.sub(r"\n\s*\n+", "\n", value)
    return value.strip()


def _clean_result_url(url):
    url = str(url or "").strip()
    if url.startswith("//"):
        url = "https:" + url

    parsed = urlparse(url)

    if parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/l/"):
        target = parse_qs(parsed.query).get("uddg")
        if target:
            url = target[0]
            parsed = urlparse(url)

    return url if parsed.scheme in {"http", "https"} else ""


def _http_text(url, *, data=None, headers=None):
    request_headers = {
        "User-Agent": WEB_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/json,text/plain;q=0.9,*/*;q=0.5",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    if headers:
        request_headers.update(headers)

    request = Request(
        url,
        data=data,
        headers=request_headers,
        method="POST" if data is not None else "GET",
    )

    with urlopen(request, timeout=WEB_TIMEOUT_SECONDS) as response:
        raw = response.read(WEB_MAX_RESPONSE_BYTES + 1)
        transport_truncated = len(raw) > WEB_MAX_RESPONSE_BYTES
        raw = raw[:WEB_MAX_RESPONSE_BYTES]
        charset = response.headers.get_content_charset() or "utf-8"

        return {
            "url": response.geturl(),
            "content_type": (response.headers.get_content_type() or "").lower(),
            "text": raw.decode(charset, errors="replace"),
            "transport_truncated": transport_truncated,
        }


def _web_search_results(query, max_results):
    response = _http_text(
        WEB_SEARCH_URL,
        data=urlencode({"q": query, "b": ""}).encode("utf-8"),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": "https://html.duckduckgo.com/",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
        },
    )

    lowered = response["text"].lower()
    if "captcha" in lowered or "anomaly-modal" in lowered:
        raise RuntimeError("Arama motoru doğrulama ekranı döndürdü.")

    parser = _SearchParser()
    parser.feed(response["text"])
    parser.close()

    results = []
    seen = set()

    for item in parser.results:
        if item["url"] in seen:
            continue

        seen.add(item["url"])
        results.append(item)

        if len(results) >= max_results:
            break

    if not results:
        raise RuntimeError("Arama motorundan kullanılabilir sonuç alınamadı.")

    return results


def _compact_search_results(results):
    compact = []

    for item in results[:WEB_SEARCH_MAX_RESULTS]:
        content = _clean_text(item.get("content", ""))
        truncated = len(content) > WEB_SEARCH_RESULT_CONTENT_MAX_CHARS

        if truncated:
            content = (
                content[:WEB_SEARCH_RESULT_CONTENT_MAX_CHARS].rstrip()
                + "\n[İÇERİK KISALTILDI]"
            )

        item_out = {
            "title": _clean_text(item.get("title", "")),
            "url": str(item.get("url", "") or "").strip(),
            "content": content,
        }

        if truncated:
            item_out["content_truncated"] = True

        candidate = [*compact, item_out]
        serialized = json.dumps(
            {"results": candidate},
            ensure_ascii=False,
            separators=(",", ":"),
        )

        if len(serialized) > WEB_SEARCH_TRANSPORT_MAX_CHARS:
            break

        compact.append(item_out)

    return json.dumps(
        {"results": compact},
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _html_to_text(body):
    title_match = re.search(
        r"<title\b[^>]*>(.*?)</title>",
        body,
        flags=re.IGNORECASE | re.DOTALL,
    )
    title = _clean_text(
        html.unescape(re.sub(r"<[^>]+>", " ", title_match.group(1)))
    ) if title_match else ""

    body = re.sub(
        r"<(script|style|svg|canvas|template)\b.*?</\1>",
        " ",
        body,
        flags=re.IGNORECASE | re.DOTALL,
    )
    body = re.sub(
        r"</?(p|div|li|br|section|article|h[1-6])\b[^>]*>",
        "\n",
        body,
        flags=re.IGNORECASE,
    )
    body = re.sub(r"<[^>]+>", " ", body)

    return title, _clean_text(html.unescape(body))


def _web_fetch(url):
    parsed = urlparse(str(url or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Yalnız http:// veya https:// adresleri açılabilir.")

    response = _http_text(parsed.geturl())
    content_type = response["content_type"]
    body = response["text"]

    if "html" in content_type or "<html" in body[:500].lower():
        title, content = _html_to_text(body)
    elif content_type.startswith("text/") or content_type in {
        "application/json",
        "application/ld+json",
        "application/xml",
        "application/rss+xml",
        "application/atom+xml",
    }:
        title = ""
        content = _clean_text(body)
    else:
        return (
            "[INTERNET HATA] web_fetch metin tabanlı olmayan içerik döndürdü: "
            f"{content_type or 'bilinmeyen içerik türü'}"
        )

    truncated = len(content) > WEB_FETCH_CONTENT_MAX_CHARS
    if truncated:
        content = (
            content[:WEB_FETCH_CONTENT_MAX_CHARS].rstrip()
            + "\n[WEB_FETCH İÇERİK SINIRI: sayfa kısaltıldı]"
        )

    payload = {
        "url": response["url"],
        "title": title,
        "content": content,
    }

    if truncated or response["transport_truncated"]:
        payload["content_truncated"] = True

    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _internet_error(error):
    if isinstance(error, HTTPError):
        try:
            detail = error.read().decode("utf-8", errors="replace").strip()
        except Exception:
            detail = ""

        return f"[INTERNET HATA] HTTP {error.code}: {detail or error.reason}"

    if isinstance(error, URLError):
        return f"[INTERNET HATA] {error.reason}"

    return f"[INTERNET HATA] {type(error).__name__}: {error}"


def internet_araci_calistir(tool_name, arguments):
    arguments = arguments or {}

    if tool_name == "web_search":
        query = str(arguments.get("query", "")).strip()
        if not query:
            return "[INTERNET HATA] web_search için query boş."

        max_results = arguments.get("max_results")
        try:
            max_results = int(max_results)
        except (TypeError, ValueError):
            max_results = WEB_SEARCH_DEFAULT_MAX_RESULTS

        max_results = max(1, min(WEB_SEARCH_MAX_RESULTS, max_results))

        print(
            f"[QWEN WEB SEARCH] {query} | max_results={max_results}",
            flush=True,
        )

        try:
            return _compact_search_results(
                _web_search_results(query, max_results)
            )
        except Exception as error:
            return _internet_error(error)

    if tool_name == "web_fetch":
        url = str(arguments.get("url", "")).strip()
        if not url:
            return "[INTERNET HATA] web_fetch için url boş."

        print(f"[QWEN WEB FETCH] {url}", flush=True)

        try:
            return _web_fetch(url)
        except Exception as error:
            return _internet_error(error)

    if tool_name == "image_search":
        query = str(arguments.get("query", "")).strip()
        if not query:
            return "[INTERNET HATA] image_search için query boş."

        max_results = arguments.get("max_results")
        try:
            max_results = int(max_results)
        except (TypeError, ValueError):
            max_results = IMAGE_SEARCH_DEFAULT_MAX_RESULTS

        max_results = max(1, min(IMAGE_SEARCH_MAX_RESULTS, max_results))

        print(
            f"[QWEN IMAGE SEARCH] {query} | max_results={max_results}",
            flush=True,
        )

        try:
            web_results = _web_search_results(
                query,
                max(WEB_SEARCH_DEFAULT_MAX_RESULTS, max_results),
            )

            return image_search_from_web_results(
                query,
                max_results,
                json.dumps(
                    {"results": web_results},
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                WEB_SEARCH_RESULT_CONTENT_MAX_CHARS,
            )
        except Exception as error:
            return _internet_error(error)

    return f"[TOOL HATA] Bilinmeyen internet aracı: {tool_name}"
