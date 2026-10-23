from __future__ import annotations

from .qwen_ayarlar import CODER_MODEL, DAILY_MODEL


# BLOK BAŞLIĞI: KOD GÖREVİ ALGILAMA - BAŞLANGIÇ

CODE_CONTEXT_TERMS = (
    "kod",
    "c++",
    "cpp",
    "c#",
    "python",
    "javascript",
    "typescript",
    "java",
    "html",
    "css",
    "sql",
    "unreal engine",
    "unity",
    "blueprint",
    "api",
    "script",
    "fonksiyon",
    "function",
    "class",
    "sınıf",
    "uygulama",
    "program",
    "web sitesi",
    ".py",
    ".js",
    ".ts",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
    ".java",
    "```",
)


CODE_ACTION_TERMS = (
    "yaz",
    "hazırla",
    "hazirla",
    "oluştur",
    "olustur",
    "geliştir",
    "gelistir",
    "düzelt",
    "duzelt",
    "kodla",
    "refactor",
    "debug",
    "hata ayıkla",
    "hata ayikla",
    "implement",
    "uygula",
    "optimize",
    "optimizasyon",
    "çalışmıyor",
    "calismiyor",
    "hata veriyor",
    "neden çalışmıyor",
    "neden calismiyor",
)


DIRECT_CODE_TASK_TERMS = (
    "kod yaz",
    "kodu yaz",
    "kodunu yaz",
    "kodla",
    "kodu düzelt",
    "kodu duzelt",
    "kodunu düzelt",
    "kodunu duzelt",
    "kod hatası",
    "kod hatasi",
    "bu kod neden",
)


def kod_gorevi_mi(text):
    value = str(text or "").casefold()

    if any(term in value for term in DIRECT_CODE_TASK_TERMS):
        return True

    has_code_context = any(
        term in value
        for term in CODE_CONTEXT_TERMS
    )

    has_code_action = any(
        term in value
        for term in CODE_ACTION_TERMS
    )

    return has_code_context and has_code_action


# BLOK BAŞLIĞI: KOD GÖREVİ ALGILAMA - BİTİŞ

def model_rolu_sec(model_mode, text):
    mode = str(model_mode or "auto").strip().casefold()

    if mode == "normal":
        return DAILY_MODEL

    if mode == "kod":
        return CODER_MODEL

    return CODER_MODEL if kod_gorevi_mi(text) else DAILY_MODEL
