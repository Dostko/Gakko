from __future__ import annotations

import json
import time
from urllib.error import HTTPError, URLError
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

INTERNET_TOOL_NAMES = frozenset({"web_search", "web_fetch"})

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

    return f"[TOOL HATA] Bilinmeyen internet aracı: {tool_name}"
