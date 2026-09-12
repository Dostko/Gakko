from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
import json
from urllib.parse import quote, urljoin, urlsplit
from urllib.request import Request, urlopen


IMAGE_SEARCH_DEFAULT_MAX_RESULTS = 3
IMAGE_SEARCH_MAX_RESULTS = 5
IMAGE_TIMEOUT_SECONDS = 8
IMAGE_PAGE_MAX_BYTES = 1024 * 1024
IMAGE_CANDIDATES_PER_PAGE = 2
IMAGE_SEARCH_ALLOWED_MIME = frozenset({
    "image/jpeg", "image/png", "image/webp", "image/gif", "image/svg+xml",
})


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
        with urlopen(
            Request(page_url, headers=headers),
            timeout=IMAGE_TIMEOUT_SECONDS,
        ) as response:
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
            with urlopen(
                Request(direct_url, headers=headers),
                timeout=IMAGE_TIMEOUT_SECONDS,
            ) as response:
                mime = response.headers.get_content_type()
                direct_url = _image_http_url(response.geturl())

                if (
                    not direct_url
                    or mime not in IMAGE_SEARCH_ALLOWED_MIME
                    or not response.read(64)
                ):
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


def image_search_from_web_results(
    query,
    max_results,
    content,
    result_content_max_chars,
):
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
            "content": str(item.get("content") or "")[:result_content_max_chars],
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
