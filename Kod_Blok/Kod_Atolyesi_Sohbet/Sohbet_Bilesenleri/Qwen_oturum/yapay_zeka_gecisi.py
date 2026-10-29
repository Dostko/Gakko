from __future__ import annotations

from .qwen_ayarlar import (
    NORMAL_MODEL,
    YUKSEK_MODEL,
    _CANCELLED,
)
from .strada import (
    strata_chat,
    strata_modelini_hazirla,
    strata_motorunu_durdur,
)


# BLOK BAŞLIĞI: MODEL GEÇİŞ KAPISI - BAŞLANGIÇ


def _aktif_model_rolu(session):
    role = str(
        getattr(session, "_active_model_role", "") or ""
    ).strip().casefold()

    if role in {NORMAL_MODEL, YUKSEK_MODEL}:
        return role

    fallback = str(
        getattr(session, "_model_mode", NORMAL_MODEL)
        or NORMAL_MODEL
    ).strip().casefold()

    if fallback in {NORMAL_MODEL, YUKSEK_MODEL}:
        return fallback

    return NORMAL_MODEL


def modeli_hazirla(session, model):
    model_name = str(model or "").strip().casefold()

    if model_name not in {NORMAL_MODEL, YUKSEK_MODEL}:
        raise ValueError(
            f"Bilinmeyen GAKKO model rolü: {model_name}"
        )

    ready = strata_modelini_hazirla(
        session,
        model_name,
    )

    if ready is _CANCELLED:
        return _CANCELLED

    session._active_model_role = model_name
    return ready


def model_chat(session, **chat_arguments):
    model_role = _aktif_model_rolu(session)

    if model_role not in {NORMAL_MODEL, YUKSEK_MODEL}:
        raise RuntimeError(
            f"Aktif GAKKO model rolü çözülemedi: {model_role}"
        )

    return strata_chat(
        session,
        **chat_arguments,
    )


def model_motorunu_durdur(session):
    try:
        result = strata_motorunu_durdur(session)
    finally:
        session._active_model_role = None

    return result


def uzman_model_cagir(
    session,
    model,
    **chat_arguments,
):
    ready = modeli_hazirla(
        session,
        model,
    )

    if ready is _CANCELLED:
        return _CANCELLED

    return model_chat(
        session,
        **chat_arguments,
    )

# BLOK BAŞLIĞI: MODEL GEÇİŞ KAPISI - BİTİŞ
