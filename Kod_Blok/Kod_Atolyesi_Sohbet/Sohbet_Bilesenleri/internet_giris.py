from __future__ import annotations

import html
import json
import re
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from .internet_kapisi.image_arama import (
    IMAGE_SEARCH_DEFAULT_MAX_RESULTS,
    IMAGE_SEARCH_MAX_RESULTS,
    image_search_from_web_results,
)


WEB_SEARCH_URL = "http://127.0.0.1:8888/search"
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
WEB_PRODUCT_TEXT_MAX_CHARS = 6000
WEB_PRODUCT_DATA_MAX_CHARS = 8000
WEB_ERROR_MAX_CHARS = 2000

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


def _clean_text(value):
    value = re.sub(r"[ \t\r\f\v]+", " ", str(value or ""))
    value = re.sub(r"\n\s*\n+", "\n", value)
    return value.strip()


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
    search_url = f"{WEB_SEARCH_URL}?{urlencode({'q': query, 'format': 'json'})}"
    response = _http_text(search_url)

    try:
        payload = json.loads(response["text"])
    except (json.JSONDecodeError, TypeError) as error:
        raise RuntimeError("SearXNG geçersiz JSON döndürdü.") from error

    raw_results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(raw_results, list):
        raise RuntimeError("SearXNG sonuç listesi döndürmedi.")

    results = []
    seen = set()

    for item in raw_results:
        if not isinstance(item, dict):
            continue

        title = _clean_text(item.get("title", ""))
        url = str(item.get("url", "") or "").strip()
        parsed = urlparse(url)

        if not title or parsed.scheme not in {"http", "https"} or not parsed.netloc:
            continue
        if url in seen:
            continue

        seen.add(url)
        results.append(
            {
                "title": title,
                "url": url,
                "content": _clean_text(item.get("content", "")),
            }
        )

        if len(results) >= max_results:
            break

    if not results:
        raise RuntimeError("SearXNG kullanılabilir arama sonucu döndürmedi.")

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


# BLOK BAŞLIĞI: YAPILANDIRILMIŞ ÜRÜN VERİSİ - BAŞLANGIÇ
class _JsonLdParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.documents = []
        self.parts = None

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            content_type = dict(attrs).get("type") or ""
            if content_type.split(";", 1)[0].strip().lower() == "application/ld+json":
                self.parts = []

    def handle_data(self, data):
        if self.parts is not None:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.parts is not None:
            try:
                self.documents.append(json.loads("".join(self.parts)))
            except (ValueError, RecursionError):
                pass
            self.parts = None


def _product_data(body):
    parser = _JsonLdParser()
    parser.feed(body)
    nodes, references = [], {}
    pending = list(parser.documents)
    while pending:
        node = pending.pop()
        if isinstance(node, list):
            pending.extend(reversed(node))
        elif isinstance(node, dict):
            nodes.append(node)
            if isinstance(node.get("@id"), str) and len(node) > 1:
                references[node["@id"]] = node
            pending.extend(reversed(list(node.values())))

    fields = (
        "@type", "name", "sku", "mpn", "model", "gtin", "gtin13", "gtin14",
        "price", "priceCurrency", "availability", "seller", "brand", "url",
        "lowPrice", "highPrice", "offerCount", "priceValidUntil", "itemCondition",
        "offers", "priceSpecification", "itemOffered",
    )

    def select(value, budget, depth=0, seen=frozenset()):
        if depth > 6 or budget[0] < 8:
            return None
        budget[0] -= 4
        if isinstance(value, dict):
            reference = value.get("@id")
            if isinstance(reference, str) and reference in references:
                if reference in seen:
                    return None
                value = {**references[reference], **value}
                seen = seen | {reference}
            result = {}
            for key in fields:
                if key in value and budget[0] > len(key) + 8:
                    budget[0] -= len(key) + 4
                    chosen = select(value[key], budget, depth + 1, seen)
                    if chosen is not None:
                        result[key] = chosen
            return result or None
        if isinstance(value, list):
            result = [select(item, budget, depth + 1, seen) for item in value[:5]]
            return [item for item in result if item is not None] or None
        if isinstance(value, (str, int, float)) and not isinstance(value, bool):
            # Uzun açıklama, görsel ve yorumlar bu alan listesine alınmaz.
            result = _clean_text(value)[:300] if isinstance(value, str) else value
            size = len(json.dumps(result, ensure_ascii=False))
            if size <= budget[0]:
                budget[0] -= size
                return result
        return None

    records, seen = [], set()
    for node in nodes:
        types = node.get("@type", [])
        types = types if isinstance(types, list) else [types]
        types = {str(value).rsplit("/", 1)[-1] for value in types}
        if not types.intersection({"Product", "ProductGroup", "Offer", "AggregateOffer"}):
            continue
        record = select(node, [6000])
        encoded = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        if record and encoded not in seen:
            if sum(map(len, records)) + len(encoded) + len(records) + 2 > WEB_PRODUCT_DATA_MAX_CHARS:
                break
            seen.add(encoded)
            records.append(encoded)
    return "[" + ",".join(records) + "]" if records else ""
# BLOK BAŞLIĞI: YAPILANDIRILMIŞ ÜRÜN VERİSİ - BİTİŞ


def _html_to_text(body):
    product_data = _product_data(body)
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

    content = _clean_text(html.unescape(body))
    if product_data:
        if len(content) > WEB_PRODUCT_TEXT_MAX_CHARS:
            content = (
                content[:WEB_PRODUCT_TEXT_MAX_CHARS].rstrip()
                + "\n[WEB_FETCH İÇERİK SINIRI: sayfa kısaltıldı]"
            )
        content = "[JSON-LD ÜRÜN VERİSİ]\n" + product_data + "\n\n" + content
    return title, content


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

    truncated = "[WEB_FETCH İÇERİK SINIRI: sayfa kısaltıldı]" in content
    truncated = truncated or len(content) > WEB_FETCH_CONTENT_MAX_CHARS
    if len(content) > WEB_FETCH_CONTENT_MAX_CHARS:
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
            raw = error.read(WEB_ERROR_MAX_CHARS * 4)
            _, detail = _html_to_text(raw.decode("utf-8", errors="replace"))
        except Exception:
            detail = ""
        message = f"HTTP {error.code}: {detail or error.reason}"
    elif isinstance(error, URLError):
        message = str(error.reason)
    else:
        message = f"{type(error).__name__}: {error}"

    if len(message) > WEB_ERROR_MAX_CHARS:
        message = message[:WEB_ERROR_MAX_CHARS] + " [HATA İÇERİĞİ KISALTILDI]"
    return f"[INTERNET HATA] {message}"


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
