from __future__ import annotations

import ctypes
import json
import multiprocessing
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .qwen_ayarlar import (
    NORMAL_CONTEXT_SIZE,
    NORMAL_MODEL,
    YUKSEK_CONTEXT_SIZE,
    YUKSEK_MODEL,
    _CANCELLED,
)

# BLOK BAŞLIĞI: STRATA AYARLARI - BAŞLANGIÇ

STRATA_HOST = 'http://127.0.0.1:8080'

STRATA_CHAT_URL = f'{STRATA_HOST}/v1/chat/completions'

STRATA_HEALTH_URL = f'{STRATA_HOST}/health'

STRATA_API_MODEL = 'strata'

STRATA_MODELS = {NORMAL_MODEL: {'family': 'swift', 'model': 'IQ3_XXS', 'context': NORMAL_CONTEXT_SIZE}, YUKSEK_MODEL: {'family': 'swift', 'model': 'IQ3_S', 'context': YUKSEK_CONTEXT_SIZE}}

_STRATA_PORT = '8080'

_MIN_FREE_RAM_BYTES = 36 * 1024 ** 3

_RUNTIME_WAIT_SECONDS = 180.0

# BLOK BAŞLIĞI: STRATA AYARLARI - BİTİŞ

# BLOK BAŞLIĞI: STRATA API YANIT YAPILARI - BAŞLANGIÇ

@dataclass
class _StrataToolFunction:
    name: str
    arguments: dict

@dataclass
class _StrataToolCall:
    id: str
    function: _StrataToolFunction
    type: str = 'function'

    def to_dict(self):
        return {'id': self.id, 'type': self.type, 'function': {'name': self.function.name, 'arguments': json.dumps(self.function.arguments, ensure_ascii=False, separators=(',', ':'))}}

@dataclass
class _StrataMessage:
    role: str = 'assistant'
    content: str = ''
    tool_calls: list[_StrataToolCall] = field(default_factory=list)

    def to_dict(self):
        result = {'role': self.role, 'content': self.content}
        if self.tool_calls:
            result['tool_calls'] = [tool_call.to_dict() for tool_call in self.tool_calls]
        return result

@dataclass
class _StrataChatResponse:
    message: _StrataMessage
    prompt_eval_count: int = 0
    eval_count: int = 0

# BLOK BAŞLIĞI: STRATA API YANIT YAPILARI - BİTİŞ

# BLOK BAŞLIĞI: STRATA TEMEL YARDIMCILAR - BAŞLANGIÇ

def _read_json(url, timeout=2.0):
    with urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode('utf-8'))

def _normalize_identity(value):
    return str(value or '').casefold().replace('\\', '/').replace('-', '_').replace(' ', '_')

def _context_cli_value(context_size):
    size = int(context_size)
    if size % 1024 == 0:
        return f'{size // 1024}k'
    return str(size)

def _available_ram_bytes():
    if os.name != 'nt':
        return None

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [('dwLength', ctypes.c_ulong), ('dwMemoryLoad', ctypes.c_ulong), ('ullTotalPhys', ctypes.c_ulonglong), ('ullAvailPhys', ctypes.c_ulonglong), ('ullTotalPageFile', ctypes.c_ulonglong), ('ullAvailPageFile', ctypes.c_ulonglong), ('ullTotalVirtual', ctypes.c_ulonglong), ('ullAvailVirtual', ctypes.c_ulonglong), ('ullAvailExtendedVirtual', ctypes.c_ulonglong)]
    status = MEMORYSTATUSEX()
    status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return None
    return int(status.ullAvailPhys)

def _ensure_launch_memory():
    available = _available_ram_bytes()
    if available is None or available >= _MIN_FREE_RAM_BYTES:
        return
    available_gib = available / 1024 ** 3
    raise RuntimeError(f"Strata modeli başlatılmadı: yalnızca {available_gib:.1f} GiB boş fiziksel RAM var. Bu koruma, başka bir büyük model veya ağır program açıkken ikinci modeli yükleyip Windows'u kilitlememek için devreye girdi.")

# BLOK BAŞLIĞI: STRATA TEMEL YARDIMCILAR - BİTİŞ

# BLOK BAŞLIĞI: STRATA RUNTIME BİLGİSİ - BAŞLANGIÇ

def strata_runtime_info():
    try:
        health = _read_json(STRATA_HEALTH_URL)
    except (OSError, URLError, ValueError, json.JSONDecodeError):
        return {'loaded': False, 'status': 'offline', 'max_context': 0, 'identity': ''}
    if 'loaded' not in health:
        return {'loaded': False, 'status': 'other_runtime', 'max_context': 0, 'identity': ''}
    loaded = bool(health.get('loaded'))
    status = str(health.get('status') or '').strip().casefold()
    identity_parts = [health.get('model')]
    if loaded and status == 'ok':
        try:
            props = _read_json(f'{STRATA_HOST}/props')
        except (OSError, URLError, ValueError, json.JSONDecodeError):
            props = {}
        identity_parts.extend((props.get('model'), props.get('model_id'), props.get('model_path')))
    identity = ' | '.join((str(item).strip() for item in identity_parts if str(item or '').strip()))
    try:
        max_context = int(health.get('max_context') or 0)
    except (TypeError, ValueError):
        max_context = 0
    return {'loaded': loaded, 'status': status, 'max_context': max_context, 'identity': identity}

def _runtime_matches_model(info, config):
    identity = _normalize_identity(info.get('identity'))
    expected = _normalize_identity(config.get('model'))
    return bool(identity and expected and (expected in identity))

# BLOK BAŞLIĞI: STRATA RUNTIME BİLGİSİ - BİTİŞ

# BLOK BAŞLIĞI: STRATA TERMINAL - BAŞLANGIÇ

def _strata_command_path():
    local_app_data = os.environ.get('LOCALAPPDATA')
    if local_app_data:
        candidate = Path(local_app_data) / 'Strata' / 'terminal' / 'current' / 'bin' / 'strata.cmd'
        if candidate.is_file():
            return candidate
    fallback = shutil.which('strata') or shutil.which('strata.cmd')
    if fallback:
        return Path(fallback)
    raise RuntimeError('Strata Terminal bulunamadı. Yüksek model Strata üzerinden çalışır.')

def _run_strata_cli(*args, timeout=600.0):
    strata_path = _strata_command_path()
    if os.name == 'nt' and strata_path.suffix.casefold() in {'.cmd', '.bat'}:
        comspec = os.environ.get('COMSPEC') or 'cmd.exe'
        command = [comspec, '/d', '/c', str(strata_path), *map(str, args)]
    else:
        command = [str(strata_path), *map(str, args)]
    completed = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout, check=False, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' and hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
    return {'returncode': int(completed.returncode), 'stdout': str(completed.stdout or '').strip(), 'stderr': str(completed.stderr or '').strip()}

# BLOK BAŞLIĞI: STRATA TERMINAL - BİTİŞ

# BLOK BAŞLIĞI: STRATA BAŞLATMA VE DURDURMA - BAŞLANGIÇ

def _wait_for_runtime(expected_loaded, config=None, timeout=_RUNTIME_WAIT_SECONDS):
    deadline = time.monotonic() + float(timeout)
    while time.monotonic() < deadline:
        info = strata_runtime_info()
        is_loaded = bool(info.get('loaded')) and info.get('status') == 'ok'
        if expected_loaded:
            if is_loaded and (config is None or _runtime_matches_model(info, config)):
                return info
        elif not is_loaded:
            return info
        time.sleep(0.5)
    if expected_loaded:
        expected = config.get('model') if config else 'model'
        raise RuntimeError(f'Strata {expected} modelini {float(timeout):.0f} saniye içinde hazır edemedi.')
    raise RuntimeError('Strata modeli süre içinde tamamen durdurulamadı.')

def strata_modelini_durdur():
    result = _run_strata_cli('launch', '--stop', '--output', 'json', timeout=120.0)
    if result['returncode'] != 0:
        detail = result['stderr'] or result['stdout'] or 'bilinmeyen hata'
        raise RuntimeError(f'Strata modeli durdurulamadı: {detail}')
    return _wait_for_runtime(False, timeout=90.0)

def strata_modelini_baslat(config):
    _ensure_launch_memory()
    result = _run_strata_cli('launch', '--model', config['model'], '--family', config['family'], '--context', _context_cli_value(config['context']), '--tune', 'skip', '--access', 'local', '--port', _STRATA_PORT, '--yes', '--no-tui', '--output', 'json', timeout=600.0)
    if result['returncode'] != 0:
        detail = result['stderr'] or result['stdout'] or 'bilinmeyen hata'
        raise RuntimeError(f'Strata modeli başlatılamadı: {detail}')
    try:
        payload = json.loads(result['stdout'] or '{}')
    except json.JSONDecodeError:
        payload = {}
    if isinstance(payload, dict) and payload.get('serving') is False:
        detail = payload.get('engine_problem') or payload.get('error') or result['stdout']
        raise RuntimeError(f'Strata modeli servis edemedi: {detail}')
    return _wait_for_runtime(True, config=config, timeout=_RUNTIME_WAIT_SECONDS)

def strata_modelini_hazirla(session, model):
    model_name = str(model or '').strip()
    config = STRATA_MODELS.get(model_name)
    if config is None:
        raise ValueError(f'Bilinmeyen GAKKO model rolü: {model_name}')
    if session._stopping or session._cancel_requested.is_set():
        return _CANCELLED
    info = strata_runtime_info()
    is_loaded = bool(info.get('loaded')) and info.get('status') == 'ok'
    if is_loaded and _runtime_matches_model(info, config):
        max_context = int(info.get('max_context') or 0)
        required_context = int(config['context'])
        if max_context and max_context < required_context:
            strata_modelini_durdur()
            session._strata_model_role = None
        else:
            session._strata_model_role = model_name
            session._active_context_size = max_context or required_context
            return True
    elif is_loaded:
        strata_modelini_durdur()
        session._strata_model_role = None
    info = strata_modelini_baslat(config)
    required_context = int(config['context'])
    max_context = int(info.get('max_context') or 0)
    session._strata_model_role = model_name
    session._active_context_size = max_context or required_context
    session._strata_owned = True
    return True

def strata_motorunu_durdur(session):
    if not bool(getattr(session, '_strata_owned', False)):
        return True
    try:
        strata_modelini_durdur()
    finally:
        session._strata_owned = False
        session._strata_model_role = None
    return True

# BLOK BAŞLIĞI: STRATA BAŞLATMA VE DURDURMA - BİTİŞ

# BLOK BAŞLIĞI: STRATA CHAT PAYLOAD - BAŞLANGIÇ

def _tool_arguments(value):
    if isinstance(value, dict):
        return value
    raw = str(value or '').strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as error:
        raise RuntimeError(f'Strata araç argümanları geçerli JSON değil: {raw[:240]}') from error
    if not isinstance(parsed, dict):
        raise RuntimeError('Strata araç argümanları JSON nesnesi olmalı.')
    return parsed

def _message_to_dict(message):
    if hasattr(message, 'to_dict'):
        message = message.to_dict()
    elif not isinstance(message, dict):
        role = str(getattr(message, 'role', '') or '').strip()
        content = getattr(message, 'content', '')
        tool_calls = getattr(message, 'tool_calls', None)
        message = {'role': role, 'content': content}
        if tool_calls:
            message['tool_calls'] = tool_calls
    result = dict(message)
    images = result.pop('images', None) or []
    if images:
        parts = [{'type': 'image_url', 'image_url': {'url': str(image_path)}} for image_path in images]
        content = result.get('content')
        if content not in (None, ''):
            parts.append({'type': 'text', 'text': str(content)})
        result['content'] = parts
    tool_calls = result.get('tool_calls')
    if tool_calls:
        normalized = []
        for tool_call in tool_calls:
            if hasattr(tool_call, 'to_dict'):
                normalized.append(tool_call.to_dict())
            elif isinstance(tool_call, dict):
                item = dict(tool_call)
                function = dict(item.get('function') or {})
                arguments = function.get('arguments')
                if isinstance(arguments, dict):
                    function['arguments'] = json.dumps(arguments, ensure_ascii=False, separators=(',', ':'))
                item['function'] = function
                normalized.append(item)
        result['tool_calls'] = normalized
    return result

def _build_strata_payload(chat_arguments):
    arguments = dict(chat_arguments)
    think = arguments.pop('think', None)
    arguments.pop('options', None)
    arguments.pop('keep_alive', None)
    arguments.pop('model', None)
    messages = arguments.pop('messages', [])
    payload = {'model': STRATA_API_MODEL, 'messages': [_message_to_dict(message) for message in messages], 'stream': bool(arguments.pop('stream', False))}
    tools = arguments.pop('tools', None)
    if tools:
        payload['tools'] = tools
    if think is True:
        payload['reasoning_effort'] = 'high'
    elif think is False:
        payload['reasoning_effort'] = 'none'
    for key in ('temperature', 'top_p', 'max_tokens', 'seed', 'stop', 'tool_choice'):
        if key in arguments:
            payload[key] = arguments[key]
    return payload

# BLOK BAŞLIĞI: STRATA CHAT PAYLOAD - BİTİŞ

# BLOK BAŞLIĞI: STRATA CHAT YANIT AYRIŞTIRMA - BAŞLANGIÇ

def _parse_strata_response(payload):
    choices = payload.get('choices') or []
    if not choices:
        error = payload.get('error')
        if isinstance(error, dict):
            detail = error.get('message') or str(error)
        else:
            detail = str(error or 'Strata boş yanıt döndürdü.')
        raise RuntimeError(detail)
    raw_message = choices[0].get('message') or {}
    tool_calls = []
    for item in raw_message.get('tool_calls') or []:
        function = item.get('function') or {}
        tool_calls.append(_StrataToolCall(id=str(item.get('id') or ''), type=str(item.get('type') or 'function'), function=_StrataToolFunction(name=str(function.get('name') or ''), arguments=_tool_arguments(function.get('arguments')))))
    usage = payload.get('usage') or {}
    return _StrataChatResponse(message=_StrataMessage(role=str(raw_message.get('role') or 'assistant'), content=str(raw_message.get('content') or ''), tool_calls=tool_calls), prompt_eval_count=int(usage.get('prompt_tokens') or 0), eval_count=int(usage.get('completion_tokens') or 0))

# BLOK BAŞLIĞI: STRATA CHAT YANIT AYRIŞTIRMA - BİTİŞ

# BLOK BAŞLIĞI: STRATA CHAT ÇAĞRISI - BAŞLANGIÇ

def _strata_chat_worker(connection, chat_arguments):
    try:
        payload = _build_strata_payload(chat_arguments)
        request = Request(STRATA_CHAT_URL, data=json.dumps(payload, ensure_ascii=False).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
        with urlopen(request, timeout=1800) as response:
            raw = response.read().decode('utf-8')
        connection.send(('ok', json.loads(raw)))
    except HTTPError as error:
        try:
            detail = error.read().decode('utf-8', errors='replace')
        except Exception:
            detail = str(error)
        try:
            connection.send(('error', f'HTTP {error.code}: {detail}'))
        except (BrokenPipeError, EOFError, OSError):
            pass
    except (URLError, OSError, ValueError, RuntimeError) as error:
        try:
            connection.send(('error', f'{type(error).__name__}: {error}'))
        except (BrokenPipeError, EOFError, OSError):
            pass
    except BaseException as error:
        try:
            connection.send(('error', f'{type(error).__name__}: {error}'))
        except (BrokenPipeError, EOFError, OSError):
            pass
    finally:
        connection.close()

def strata_chat(session, **kwargs):
    if session._stopping or session._cancel_requested.is_set():
        return _CANCELLED
    process_context = multiprocessing.get_context('spawn')
    receive_connection, send_connection = process_context.Pipe(duplex=False)
    process = process_context.Process(target=_strata_chat_worker, args=(send_connection, dict(kwargs)), daemon=True)
    started = False
    try:
        with session._active_process_lock:
            if session._stopping or session._cancel_requested.is_set():
                return _CANCELLED
            session._active_process = process
            process.start()
            started = True
        send_connection.close()
        while True:
            if session._stopping or session._cancel_requested.is_set():
                if process.is_alive():
                    process.terminate()
                return _CANCELLED
            if receive_connection.poll(0.05):
                try:
                    status, payload = receive_connection.recv()
                except EOFError:
                    status = None
                    payload = None
                if status == 'ok':
                    return _parse_strata_response(payload)
                if status == 'error':
                    raise RuntimeError(payload)
            if not process.is_alive():
                if receive_connection.poll(0.1):
                    continue
                raise RuntimeError(f'Strata istek süreci yanıt vermeden kapandı (çıkış kodu: {process.exitcode}).')
    finally:
        with session._active_process_lock:
            if session._active_process is process:
                session._active_process = None
        if started and process.is_alive():
            process.terminate()
        if started:
            process.join(2.0)
            if process.is_alive() and hasattr(process, 'kill'):
                process.kill()
                process.join(2.0)
        receive_connection.close()
        if not started:
            send_connection.close()

# BLOK BAŞLIĞI: STRATA CHAT ÇAĞRISI - BİTİŞ
