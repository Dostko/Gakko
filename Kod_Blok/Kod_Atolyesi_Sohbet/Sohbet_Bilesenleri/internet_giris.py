from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


OLLAMA_WEB_BASE = "http://127.0.0.1:11434/api/experimental"
WEB_TIMEOUT_SECONDS = 60

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
                        "maximum": 10,
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

    try:
        with urlopen(request, timeout=WEB_TIMEOUT_SECONDS) as response:
            content = response.read().decode("utf-8", errors="replace").strip()
            return content or "[INTERNET HATA] Ollama boş yanıt döndürdü."
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace").strip()
        return f"[INTERNET HATA] HTTP {error.code}: {detail or error.reason}"
    except URLError as error:
        return f"[INTERNET HATA] {error.reason}"
    except Exception as error:
        return f"[INTERNET HATA] {type(error).__name__}: {error}"


def internet_araci_calistir(tool_name, arguments):
    arguments = arguments or {}

    if tool_name == "web_search":
        query = str(arguments.get("query", "")).strip()
        if not query:
            return "[INTERNET HATA] web_search için query boş."

        print(
            f"[QWEN WEB SEARCH] {query}",
            flush=True,
        )

        payload = {"query": query}
        max_results = arguments.get("max_results")
        if max_results is not None:
            payload["max_results"] = max_results

        return _post_json("web_search", payload)

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
