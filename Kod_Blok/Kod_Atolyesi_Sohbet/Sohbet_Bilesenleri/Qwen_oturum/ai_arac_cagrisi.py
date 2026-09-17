from __future__ import annotations

from .qwen_ayarlar import (
    CODER_MODEL,
    OLLAMA_CONTEXT_SIZE,
    _CANCELLED,
)


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


CODER_SYSTEM_PROMPT = (
    "Sen GAKKO'nun Kodcu uzman modelisin. "
    "Sana yalnız kodlama, yazılım geliştirme veya teknik programlama görevi verilir. "
    "Görevi teknik olarak çöz. Görmediğin proje dosyalarını veya yapısını uydurma. "
    "Mevcut bağlam yeterli değilse bunu açıkça belirt. "
    "Nihai kullanıcı cevabı yazma; ana Günlük modelin kullanacağı temiz ve uygulanabilir "
    "teknik çözümü üret."
)


def kodcu_ai_calistir(session, gorev):
    task = str(gorev or "").strip()

    if not task:
        return "[KODCU AI HATA] Görev boş."

    print(
        f"[GAKKO KODCU] Model çağrısı: {CODER_MODEL}",
        flush=True,
    )

    response = session._chat(
        model=CODER_MODEL,
        messages=[
            {
                "role": "system",
                "content": CODER_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": task,
            },
        ],
        stream=False,
        options={"num_ctx": OLLAMA_CONTEXT_SIZE},
    )

    if response is _CANCELLED:
        return _CANCELLED

    content = str(response.message.content or "").strip()

    if not content:
        return f"[KODCU AI HATA] {CODER_MODEL} boş çıktı üretti."

    return content