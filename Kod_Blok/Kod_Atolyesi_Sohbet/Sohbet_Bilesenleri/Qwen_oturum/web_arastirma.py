"""Yalnız bir isteğin toplam web araç çağrısı sınırını uygular."""
from __future__ import annotations

WEB_RESEARCH_TOOL_NAMES = frozenset({'web_search', 'web_fetch'})
WEB_USAGE_LIMIT_MESSAGE = (
    '[INTERNET KULLANIM SINIRI] web_search/web_fetch sınırı doldu. '
    'Yeni internet çağrısı yapma; mevcut kaynaklarla nihai cevabı üret. '
    'Kaynak yetersizse doğrulanamayan kısmı açıkça belirt.'
)


class WebArastirma:
    def __init__(self, limit):
        self.limit = int(limit)
        self.calls = 0

    def before(self, name, arguments):
        if name in WEB_RESEARCH_TOOL_NAMES and self.calls >= self.limit:
            return WEB_USAGE_LIMIT_MESSAGE
        return None

    def after(self, name, arguments, result):
        if name not in WEB_RESEARCH_TOOL_NAMES:
            return result
        self.calls += 1
        if self.calls >= self.limit:
            return f'{result}\n\n{WEB_USAGE_LIMIT_MESSAGE}'
        return result
