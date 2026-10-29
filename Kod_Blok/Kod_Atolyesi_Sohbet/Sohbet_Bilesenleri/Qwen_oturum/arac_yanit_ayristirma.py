"""API content alanına sızan tam araç mesajlarını standart çağrıya çevirir."""
from __future__ import annotations

import json
import re
import uuid


# BLOK BAŞLIĞI: METİN ARAÇ ÇAĞRISI AYRIŞTIRMA - BAŞLANGIÇ

def _validate(value, schema):
    expected = schema.get('type')
    types = {
        'string': lambda v: isinstance(v, str),
        'object': lambda v: isinstance(v, dict),
        'array': lambda v: isinstance(v, list),
        'boolean': lambda v: isinstance(v, bool),
        'integer': lambda v: isinstance(v, int) and not isinstance(v, bool),
        'number': lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
        'null': lambda v: v is None,
    }
    if isinstance(expected, str) and expected in types and not types[expected](value):
        raise ValueError(f'Argüman türü {expected} olmalı.')
    if 'enum' in schema and value not in schema['enum']:
        raise ValueError('Argüman izin verilen değerlerden biri değil.')
    if isinstance(value, dict):
        properties = schema.get('properties') or {}
        if any(key not in value for key in schema.get('required', [])):
            raise ValueError('Zorunlu araç argümanı eksik.')
        for key, item in value.items():
            if key not in properties:
                raise ValueError(f'Tanımsız araç argümanı: {key}')
            _validate(item, properties[key])
    elif isinstance(value, list):
        for item in value:
            _validate(item, schema.get('items') or {})


def _parse_body(body, schemas):
    if body.startswith('{'):
        call = json.loads(body)
        name, arguments = call['name'], call['arguments']
    else:
        function = re.fullmatch(r'<function=([\w.-]+)>\s*(.*?)\s*</function>', body, re.S)
        if function is None:
            raise ValueError('Araç function bloğu geçersiz.')
        name, parameters = function.groups()
        arguments = {}
        cursor = 0
        for match in re.finditer(r'<parameter=([\w.-]+)>\s*(.*?)\s*</parameter>', parameters, re.S):
            if parameters[cursor:match.start()].strip():
                raise ValueError('Araç parametre bloğu geçersiz.')
            key, raw = match.groups()
            if key in arguments:
                raise ValueError(f'Tekrarlanan araç argümanı: {key}')
            prop = (schemas.get(name, {}).get('properties') or {}).get(key, {})
            arguments[key] = raw if prop.get('type') == 'string' else json.loads(raw)
            cursor = match.end()
        if parameters[cursor:].strip():
            raise ValueError('Kapanmamış araç parametresi.')
    if not isinstance(name, str) or name not in schemas:
        raise ValueError(f'Bu turda sunulmayan araç: {name}')
    if not isinstance(arguments, dict):
        raise ValueError('Araç argümanları nesne olmalı.')
    _validate(arguments, schemas[name])
    return {'id': 'call_' + uuid.uuid4().hex, 'type': 'function',
            'function': {'name': name, 'arguments': json.dumps(arguments, ensure_ascii=False)}}


def normalize_tool_message(message, tools):
    """Yalnız tamamı çağrı bloklarından oluşan mesajları dönüştürür.

    Doğal dil ve kod örnekleri çalıştırılmaz. Native tool_calls korunur.
    Bozuk çağrılar nihai yanıt olarak kabul edilmez; açık hata döner.
    """
    if message.get('tool_calls'):
        return message
    content = str(message.get('content') or '')
    text = content.strip()
    if not text.startswith('<tool_call>'):
        return message
    schemas = {t['function']['name']: t['function'].get('parameters') or {}
               for t in tools or [] if isinstance(t, dict) and isinstance(t.get('function'), dict)}
    try:
        calls = []
        cursor = 0
        for match in re.finditer(r'<tool_call>\s*(.*?)\s*</tool_call>', text, re.S):
            if text[cursor:match.start()].strip():
                raise ValueError('Araç blokları arasında beklenmeyen metin.')
            calls.append(_parse_body(match.group(1), schemas))
            cursor = match.end()
        if not calls or text[cursor:].strip():
            raise ValueError('Eksik veya kapanmamış tool_call bloğu.')
    except (ValueError, TypeError, KeyError) as exc:
        raise RuntimeError(f'Modelin metin araç çağrısı işlenemedi: {exc}') from exc
    return {**message, 'content': '', 'tool_calls': calls}

# BLOK BAŞLIĞI: METİN ARAÇ ÇAĞRISI AYRIŞTIRMA - BİTİŞ
