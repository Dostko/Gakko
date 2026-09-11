from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlsplit
from urllib.request import Request, urlopen


OLLAMA_WEB_BASE = "http://127.0.0.1:11434/api/experimental"
WEB_TIMEOUT_SECONDS = 60

# web_search sonuçları kaynak seçimi için kullanılır. Ayrıntı gerekiyorsa Qwen
# seçtiği URL'yi web_fetch ile açar. Bu nedenle her arama sonucunun tam sayfa
# içeriğini modele taşımak yerine başlık + URL + sınırlı içerik taşınır.
WEB_SEARCH_DEFAULT_MAX_RESULTS = 3
WEB_SEARCH_MAX_RESULTS = 3
WEB_SEARCH_RESULT_CONTENT_MAX_CHARS = 600
WEB_SEARCH_FALLBACK_MAX_CHARS = 6000
WEB_SEARCH_TRANSPORT_MAX_CHARS = 3000

IMAGE_SEARCH_DEFAULT_MAX_RESULTS = 3
IMAGE_SEARCH_MAX_RESULTS = 5
IMAGE_TIMEOUT_SECONDS = 8
IMAGE_PAGE_MAX_BYTES = 1024 * 1024
IMAGE_CANDIDATES_PER_PAGE = 2
IMAGE_SEARCH_ALLOWED_MIME = frozenset({
    "image/jpeg", "image/png", "image/webp", "image/gif", "image/svg+xml",
})

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


def _post_json(endpoint, payload):
    request = Request(
        f"{OLLAMA_WEB_BASE}/{endpoint}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    started_at = time.perf_counter()

    try:
        with urlopen(request, timeout=WEB_TIMEOUT_SECONDS) as response:
            raw_content = response.read()
            elapsed = time.perf_counter() - started_at

            content = raw_content.decode(
                "utf-8",
                errors="replace",
            ).strip()

            print(
                "[QWEN WEB ÖLÇÜM] "
                f"endpoint={endpoint} | "
                f"süre={elapsed:.2f} sn | "
                f"karakter={len(content)} | "
                f"bayt={len(raw_content)}",
                flush=True,
            )

            return content or "[INTERNET HATA] Ollama boş yanıt döndürdü."

    except HTTPError as error:
        elapsed = time.perf_counter() - started_at

        detail = error.read().decode(
            "utf-8",
            errors="replace",
        ).strip()

        print(
            "[QWEN WEB ÖLÇÜM] "
            f"endpoint={endpoint} | "
            f"süre={elapsed:.2f} sn | "
            f"HTTP={error.code}",
            flush=True,
        )

        return (
            f"[INTERNET HATA] HTTP {error.code}: "
            f"{detail or error.reason}"
        )

    except URLError as error:
        elapsed = time.perf_counter() - started_at

        print(
            "[QWEN WEB ÖLÇÜM] "
            f"endpoint={endpoint} | "
            f"süre={elapsed:.2f} sn | "
            "durum=URL_ERROR",
            flush=True,
        )

        return f"[INTERNET HATA] {error.reason}"

    except Exception as error:
        elapsed = time.perf_counter() - started_at

        print(
            "[QWEN WEB ÖLÇÜM] "
            f"endpoint={endpoint} | "
            f"süre={elapsed:.2f} sn | "
            f"durum={type(error).__name__}",
            flush=True,
        )

        return (
            f"[INTERNET HATA] "
            f"{type(error).__name__}: {error}"
        )


class _PageImageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.images = []

    def handle_starttag(self, tag, attrs):
        if tag != "meta":
            return
        attrs = dict(attrs)
        name = str(attrs.get("property") or "").lower()
        if name in {"og:image", "og:image:url", "og:image:secure_url"}:
            value = str(attrs.get("content") or "").strip()
            if value and value not in self.images:
                self.images.append(value)


def _image_http_url(value, base=""):
    try:
        value = urljoin(base, str(value or "").strip())
        parts = urlsplit(value)
    except ValueError:
        return ""
    if (
        parts.scheme not in {"http", "https"}
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
        or any(char in value for char in "\r\n\\")
    ):
        return ""
    return quote(value, safe=":/?#[]@!$&'()*+,;=%-._~")


def _image_from_source(source):
    """Sayfanın ilan ettiği görseli getirir; konu hakkında karar vermez."""
    page_url = _image_http_url(source.get("url"))
    if not page_url:
        return None
    headers = {"User-Agent": "GAKKO/1.0", "Accept": "text/html,image/*"}
    try:
        with urlopen(Request(page_url, headers=headers), timeout=IMAGE_TIMEOUT_SECONDS) as response:
            base = _image_http_url(response.geturl())
            if not base:
                return None
            content_type = response.headers.get_content_type()
            if content_type in IMAGE_SEARCH_ALLOWED_MIME:
                candidates = [base] if response.read(64) else []
            elif content_type in {"text/html", "application/xhtml+xml"}:
                raw = response.read(IMAGE_PAGE_MAX_BYTES)
                encoding = response.headers.get_content_charset() or "utf-8"
                parser = _PageImageParser()
                parser.feed(raw.decode(encoding, errors="replace"))
                candidates = parser.images[:IMAGE_CANDIDATES_PER_PAGE]
            else:
                return None
    except (OSError, ValueError, LookupError) as error:
        print(f"[QWEN IMAGE SAYFA HATA] {page_url} | {error}", flush=True)
        return None

    for reference in candidates:
        direct_url = _image_http_url(reference, base)
        if not direct_url:
            continue
        try:
            with urlopen(Request(direct_url, headers=headers), timeout=IMAGE_TIMEOUT_SECONDS) as response:
                mime = response.headers.get_content_type()
                direct_url = _image_http_url(response.geturl())
                if not direct_url or mime not in IMAGE_SEARCH_ALLOWED_MIME or not response.read(64):
                    continue
        except (OSError, ValueError) as error:
            print(f"[QWEN IMAGE ADRES HATA] {direct_url} | {error}", flush=True)
            continue

        caption = " ".join(str(source.get("title") or "Görsel").split())
        caption = caption.replace("\\", "").replace("[", "(").replace("]", ")")[:180]
        markdown_url = quote(direct_url, safe=":/?&=%+#@!$;,*~-._")
        return {
            "title": str(source.get("title") or ""),
            "caption": caption,
            "direct_url": direct_url,
            "source_url": page_url,
            "mime": mime,
            "markdown_image": f"![{caption}]({markdown_url})",
        }
    return None


def _web_image_search(query, max_results):
    started_at = time.perf_counter()
    content = _post_json("web_search", {
        "query": query,
        "max_results": max(WEB_SEARCH_DEFAULT_MAX_RESULTS, max_results),
    })
    if content.startswith("[INTERNET HATA]"):
        return content
    payload = json.loads(content)
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise ValueError("Görsel araması için web_search sonuç listesi gelmedi.")

    sources = []
    seen_sources = set()
    for item in payload["results"][:IMAGE_SEARCH_MAX_RESULTS]:
        if not isinstance(item, dict):
            continue
        url = _image_http_url(item.get("url"))
        if not url or url in seen_sources:
            continue
        seen_sources.add(url)
        sources.append({
            "title": str(item.get("title") or "")[:200],
            "url": url,
            "content": str(item.get("content") or "")[:WEB_SEARCH_RESULT_CONTENT_MAX_CHARS],
        })

    results = []
    if sources:
        with ThreadPoolExecutor(max_workers=3) as pool:
            found = list(pool.map(_image_from_source, sources))
        seen_images = set()
        for result in found:
            if result and result["direct_url"] not in seen_images:
                seen_images.add(result["direct_url"])
                results.append(result)
                if len(results) >= max_results:
                    break

    primary = results[0]["markdown_image"] if results else ""
    print(
        f"[QWEN IMAGE SONUÇ] kaynak={len(sources)} | görsel={len(results)} | "
        f"süre={time.perf_counter() - started_at:.2f} sn",
        flush=True,
    )
    return json.dumps({
        "query": query,
        "sources": sources,
        "results": results,
        "primary_markdown_image": primary,
        "final_answer_instruction": (
            "Bilgi için sources içeriğini kullan; görsel başlığından doğrulanmamış bilgi çıkarma. "
            "Kaynak yetersizse web_search/web_fetch kullan. "
            "results varsa konuya uygun bir markdown_image satırını final cevaba aynen ekle. "
            "results boşsa görsel bulunamadığını belirt; görsel adresi uydurma."
        ),
    }, ensure_ascii=False)


def _compact_web_search_response(content):
    """
    Ollama web_search yanıtını kaynak seçimi için gerekli boyuta indirir.

    Kaynak seçmez veya sonuç sırasını değiştirmez. Yalnız her sonucun başlık,
    URL ve sınırlı içerik bölümünü modele taşır. Ayrıntı gerektiğinde Qwen
    web_fetch çağırabilir.
    """
    if not content or content.startswith("[INTERNET HATA]"):
        return content

    try:
        payload = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        if len(content) <= WEB_SEARCH_FALLBACK_MAX_CHARS:
            return content

        compact = (
            content[:WEB_SEARCH_FALLBACK_MAX_CHARS].rstrip()
            + "\n[WEB_SEARCH TAŞIMA SINIRI: yanıt kısaltıldı]"
        )

        print(
            "[QWEN WEB TAŞIMA] "
            f"endpoint=web_search | ham={len(content)} | "
            f"modele={len(compact)} | json=geçersiz",
            flush=True,
        )
        return compact

    results = payload.get("results")
    if not isinstance(results, list):
        if len(content) <= WEB_SEARCH_FALLBACK_MAX_CHARS:
            return content

        compact = (
            content[:WEB_SEARCH_FALLBACK_MAX_CHARS].rstrip()
            + "\n[WEB_SEARCH TAŞIMA SINIRI: yanıt kısaltıldı]"
        )

        print(
            "[QWEN WEB TAŞIMA] "
            f"endpoint=web_search | ham={len(content)} | "
            f"modele={len(compact)} | results=bulunamadı",
            flush=True,
        )
        return compact

    compact_results = []

    for item in results[:WEB_SEARCH_MAX_RESULTS]:
        if not isinstance(item, dict):
            continue

        title = str(item.get("title", "") or "").strip()
        url = str(item.get("url", "") or "").strip()
        result_content = str(item.get("content", "") or "").strip()

        truncated = len(result_content) > WEB_SEARCH_RESULT_CONTENT_MAX_CHARS
        if truncated:
            result_content = (
                result_content[:WEB_SEARCH_RESULT_CONTENT_MAX_CHARS].rstrip()
                + "\n[İÇERİK KISALTILDI]"
            )

        compact_item = {
            "title": title,
            "url": url,
            "content": result_content,
        }

        if truncated:
            compact_item["content_truncated"] = True

        candidate_results = [*compact_results, compact_item]
        candidate = json.dumps(
            {"results": candidate_results},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        if len(candidate) > WEB_SEARCH_TRANSPORT_MAX_CHARS:
            break

        compact_results.append(compact_item)

    compact = json.dumps(
        {"results": compact_results},
        ensure_ascii=False,
        separators=(",", ":"),
    )

    print(
        "[QWEN WEB TAŞIMA] "
        f"endpoint=web_search | sonuç={len(compact_results)} | "
        f"ham={len(content)} | modele={len(compact)}",
        flush=True,
    )

    return compact


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

        payload = {
            "query": query,
            "max_results": max_results,
        }

        result = _post_json("web_search", payload)
        return _compact_web_search_response(result)

    if tool_name == "web_fetch":
        url = str(arguments.get("url", "")).strip()
        if not url:
            return "[INTERNET HATA] web_fetch için url boş."

        print(
            f"[QWEN WEB FETCH] {url}",
            flush=True,
        )

        return _post_json("web_fetch", {"url": url})

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
            return _web_image_search(query, max_results)
        except Exception as error:
            return f"[INTERNET HATA] {type(error).__name__}: {error}"

    return f"[TOOL HATA] Bilinmeyen internet aracı: {tool_name}"
