from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .internet_kapisi.image_arama import (
    IMAGE_SEARCH_DEFAULT_MAX_RESULTS,
    IMAGE_SEARCH_MAX_RESULTS,
    image_search_from_web_results,
)


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

    try:
        with urlopen(request, timeout=WEB_TIMEOUT_SECONDS) as response:
            content = response.read().decode(
                "utf-8",
                errors="replace",
            ).strip()

            return content or "[INTERNET HATA] Ollama boş yanıt döndürdü."

    except HTTPError as error:
        detail = error.read().decode(
            "utf-8",
            errors="replace",
        ).strip()

        return (
            f"[INTERNET HATA] HTTP {error.code}: "
            f"{detail or error.reason}"
        )

    except URLError as error:
        return f"[INTERNET HATA] {error.reason}"

    except Exception as error:
        return (
            f"[INTERNET HATA] "
            f"{type(error).__name__}: {error}"
        )


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

        return (
            content[:WEB_SEARCH_FALLBACK_MAX_CHARS].rstrip()
            + "\n[WEB_SEARCH TAŞIMA SINIRI: yanıt kısaltıldı]"
        )

    results = payload.get("results")
    if not isinstance(results, list):
        if len(content) <= WEB_SEARCH_FALLBACK_MAX_CHARS:
            return content

        return (
            content[:WEB_SEARCH_FALLBACK_MAX_CHARS].rstrip()
            + "\n[WEB_SEARCH TAŞIMA SINIRI: yanıt kısaltıldı]"
        )

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

    return json.dumps(
        {"results": compact_results},
        ensure_ascii=False,
        separators=(",", ":"),
    )


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
            content = _post_json("web_search", {
                "query": query,
                "max_results": max(WEB_SEARCH_DEFAULT_MAX_RESULTS, max_results),
            })

            return image_search_from_web_results(
                query,
                max_results,
                content,
                WEB_SEARCH_RESULT_CONTENT_MAX_CHARS,
            )
        except Exception as error:
            return f"[INTERNET HATA] {type(error).__name__}: {error}"

    return f"[TOOL HATA] Bilinmeyen internet aracı: {tool_name}"
