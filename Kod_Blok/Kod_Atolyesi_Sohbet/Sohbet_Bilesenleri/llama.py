from __future__ import annotations

import base64
import ctypes
import json
import mimetypes
import multiprocessing
import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .qwen_ayarlar import NORMAL_MODEL, _CANCELLED

# BLOK BAŞLIĞI: LLAMA.CPP AYARLARI - BAŞLANGIÇ

LLAMA_HOST = 'http://127.0.0.1:9931'
LLAMA_CHAT_URL = f'{LLAMA_HOST}/v1/chat/completions'
LLAMA_HEALTH_URL = f'{LLAMA_HOST}/health'
LLAMA_API_MODEL = 'gemma4'

LLAMA_SERVER_PATH = Path(r'D:\llama\bin\llama-server.exe')
GEMMA_MODEL_PATH = Path(r'D:\Gemma\gemma-4-26B-A4B-it-Q8_0.gguf')
GEMMA_MMPROJ_PATH = Path(r'D:\Gemma\mmproj-gemma-4-26B-A4B-it-f16.gguf')
LLAMA_CONTEXT_SIZE = 32768

_LLAMA_URL = urlparse(LLAMA_HOST)
_LLAMA_BIND_HOST = _LLAMA_URL.hostname or '127.0.0.1'
_LLAMA_PORT = str(_LLAMA_URL.port or 9931)
_MIN_FREE_RAM_BYTES = 36 * 1024 ** 3
_RUNTIME_WAIT_SECONDS = 180.0

# BLOK BAŞLIĞI: LLAMA.CPP AYARLARI - BİTİŞ

# BLOK BAŞLIĞI: LLAMA API YANIT YAPILARI - BAŞLANGIÇ

@dataclass
class _LlamaToolFunction:
    name: str
    arguments: dict

@dataclass
class _LlamaToolCall:
    id: str
    function: _LlamaToolFunction
    type: str = 'function'

    def to_dict(self):
        return {'id': self.id, 'type': self.type, 'function': {'name': self.function.name, 'arguments': json.dumps(self.function.arguments, ensure_ascii=False, separators=(',', ':'))}}

@dataclass
class _LlamaMessage:
    role: str = 'assistant'
    content: str = ''
    tool_calls: list[_LlamaToolCall] = field(default_factory=list)

    def to_dict(self):
        result = {'role': self.role, 'content': self.content}
        if self.tool_calls:
            result['tool_calls'] = [tool_call.to_dict() for tool_call in self.tool_calls]
        return result

@dataclass
class _LlamaChatResponse:
    message: _LlamaMessage
    prompt_eval_count: int = 0
    eval_count: int = 0

# BLOK BAŞLIĞI: LLAMA API YANIT YAPILARI - BİTİŞ

# BLOK BAŞLIĞI: LLAMA TEMEL YARDIMCILAR - BAŞLANGIÇ

def _read_json(url, timeout=2.0):
    with urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode('utf-8'))

def _normalize_identity(value):
    return str(value or '').casefold().replace('\\', '/').replace('-', '_').replace(' ', '_')

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
    raise RuntimeError(f"Llama modeli başlatılmadı: yalnızca {available_gib:.1f} GiB boş fiziksel RAM var. Bu koruma, başka bir büyük model veya ağır program açıkken ikinci modeli yükleyip Windows'u kilitlememek için devreye girdi.")

# BLOK BAŞLIĞI: LLAMA TEMEL YARDIMCILAR - BİTİŞ

# BLOK BAŞLIĞI: LLAMA RUNTIME BİLGİSİ - BAŞLANGIÇ

def llama_runtime_info():
    try:
        health = _read_json(LLAMA_HEALTH_URL)
    except HTTPError as error:
        if error.code == 503:
            return {'loaded': False, 'status': 'loading', 'max_context': 0, 'identity': ''}
        return {'loaded': False, 'status': 'offline', 'max_context': 0, 'identity': ''}
    except (OSError, URLError, ValueError, json.JSONDecodeError):
        return {'loaded': False, 'status': 'offline', 'max_context': 0, 'identity': ''}

    if 'loaded' in health:
        return {'loaded': False, 'status': 'other_runtime', 'max_context': 0, 'identity': ''}

    status = str(health.get('status') or '').strip().casefold()
    loaded = status == 'ok'
    props = {}
    if loaded:
        try:
            props = _read_json(f'{LLAMA_HOST}/props')
        except (OSError, URLError, ValueError, json.JSONDecodeError):
            props = {}

    identity_parts = (props.get('model_alias'), props.get('model_path'))
    identity = ' | '.join(str(item).strip() for item in identity_parts if str(item or '').strip())
    settings = props.get('default_generation_settings')
    if not isinstance(settings, dict):
        settings = {}
    try:
        max_context = int(settings.get('n_ctx') or 0)
    except (TypeError, ValueError):
        max_context = 0
    return {'loaded': loaded, 'status': status, 'max_context': max_context, 'identity': identity}

def _runtime_matches_gemma(info):
    identity = _normalize_identity(info.get('identity'))
    expected_path = _normalize_identity(GEMMA_MODEL_PATH)
    expected_name = _normalize_identity(GEMMA_MODEL_PATH.name)
    expected_alias = _normalize_identity(LLAMA_API_MODEL)
    return bool(identity and (expected_path in identity or expected_name in identity or expected_alias in identity))

# BLOK BAŞLIĞI: LLAMA RUNTIME BİLGİSİ - BİTİŞ

# BLOK BAŞLIĞI: LLAMA BAŞLATMA VE DURDURMA - BAŞLANGIÇ

def _wait_for_runtime(session, expected_loaded, timeout=_RUNTIME_WAIT_SECONDS):
    deadline = time.monotonic() + float(timeout)
    while time.monotonic() < deadline:
        info = llama_runtime_info()
        process = getattr(session, '_llama_process', None)
        if process is not None:
            returncode = process.poll()
            if returncode is not None:
                session._llama_process = None
                if expected_loaded:
                    raise RuntimeError(f'llama.cpp Gemma sunucusu model hazır olmadan kapandı. Çıkış kodu: {returncode}')

        is_loaded = bool(info.get('loaded')) and info.get('status') == 'ok'
        if expected_loaded:
            if is_loaded and _runtime_matches_gemma(info):
                return info
        elif not is_loaded and info.get('status') != 'loading':
            return info
        time.sleep(0.5)

    if expected_loaded:
        raise RuntimeError(f'llama.cpp Gemma modelini {float(timeout):.0f} saniye içinde hazır edemedi.')
    raise RuntimeError('llama.cpp Gemma modeli süre içinde tamamen durdurulamadı.')

def llama_modelini_baslat(session):
    _ensure_launch_memory()
    server_path = Path(LLAMA_SERVER_PATH)
    model_path = Path(GEMMA_MODEL_PATH)
    mmproj_path = Path(GEMMA_MMPROJ_PATH)

    if not server_path.is_file():
        raise RuntimeError(f'llama-server.exe bulunamadı: {server_path}')
    if not model_path.is_file():
        raise RuntimeError(f'Gemma model dosyası bulunamadı: {model_path}')
    if not mmproj_path.is_file():
        raise RuntimeError(f'Gemma mmproj dosyası bulunamadı: {mmproj_path}')

    current = llama_runtime_info()
    if current.get('status') not in {'offline'} and not (current.get('loaded') and _runtime_matches_gemma(current)):
        raise RuntimeError(f'{_LLAMA_PORT} portunda başka bir runtime çalışıyor. Llama başlatılmadan önce o motor durdurulmalı.')

    command = [
        str(server_path),
        '--model', str(model_path),
        '--mmproj', str(mmproj_path),
        '-c', str(int(LLAMA_CONTEXT_SIZE)),
        '-ngl', 'auto',
        '--fit', 'on',
        '--fit-ctx', str(int(LLAMA_CONTEXT_SIZE)),
        '-np', '1',
        '--jinja',
        '--host', _LLAMA_BIND_HOST,
        '--port', _LLAMA_PORT,
        '--alias', LLAMA_API_MODEL,
        '--no-ui',
        '--offline',
    ]

    session._llama_process = subprocess.Popen(
        command,
        cwd=str(server_path.parent),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' and hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
    )
    session._llama_owned = True

    try:
        return _wait_for_runtime(session, True, timeout=_RUNTIME_WAIT_SECONDS)
    except Exception:
        process = getattr(session, '_llama_process', None)
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5.0)
        session._llama_process = None
        session._llama_owned = False
        raise

def llama_modelini_hazirla(session, model):
    model_name = str(model or '').strip()
    if model_name != NORMAL_MODEL:
        raise ValueError(f'Llama için bilinmeyen GAKKO model rolü: {model_name}')
    if session._stopping or session._cancel_requested.is_set():
        return _CANCELLED

    info = llama_runtime_info()
    is_loaded = bool(info.get('loaded')) and info.get('status') == 'ok'
    if is_loaded and _runtime_matches_gemma(info):
        max_context = int(info.get('max_context') or 0)
        if not max_context or max_context >= LLAMA_CONTEXT_SIZE:
            session._llama_model_role = model_name
            session._active_context_size = max_context or LLAMA_CONTEXT_SIZE
            return True
        if bool(getattr(session, '_llama_owned', False)):
            llama_motorunu_durdur(session)
        else:
            raise RuntimeError(f'Çalışan Gemma sunucusunun bağlamı {LLAMA_CONTEXT_SIZE} token için yetersiz ve bu işlem GAKKO tarafından başlatılmamış.')
    elif info.get('status') not in {'offline'}:
        raise RuntimeError(f'{_LLAMA_PORT} portunda başka bir runtime çalışıyor. Normal model başlatılmadan önce o motor durdurulmalı.')

    info = llama_modelini_baslat(session)
    max_context = int(info.get('max_context') or 0)
    session._llama_model_role = model_name
    session._active_context_size = max_context or LLAMA_CONTEXT_SIZE
    return True

def llama_motorunu_durdur(session):
    if not bool(getattr(session, '_llama_owned', False)):
        return True
    process = getattr(session, '_llama_process', None)
    try:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=15.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10.0)
        session._llama_process = None
        return _wait_for_runtime(session, False, timeout=90.0)
    finally:
        session._llama_process = None
        session._llama_owned = False
        session._llama_model_role = None

# BLOK BAŞLIĞI: LLAMA BAŞLATMA VE DURDURMA - BİTİŞ

# BLOK BAŞLIĞI: LLAMA CHAT PAYLOAD - BAŞLANGIÇ

def _tool_arguments(value):
    if isinstance(value, dict):
        return value
    raw = str(value or '').strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as error:
        raise RuntimeError(f'Llama araç argümanları geçerli JSON değil: {raw[:240]}') from error
    if not isinstance(parsed, dict):
        raise RuntimeError('Llama araç argümanları JSON nesnesi olmalı.')
    return parsed

def _image_to_data_url(image_value):
    raw_value = str(image_value or '').strip()
    if not raw_value:
        raise RuntimeError('Llama görsel yolu boş.')

    lowered = raw_value.casefold()
    if lowered.startswith('data:image/'):
        return raw_value
    if lowered.startswith(('http://', 'https://')):
        return raw_value

    image_path = Path(raw_value)
    if not image_path.is_file():
        raise RuntimeError(f'Llama görsel dosyasını bulamadı: {image_path}')

    mime_type = mimetypes.guess_type(image_path.name)[0] or 'image/png'
    encoded = base64.b64encode(image_path.read_bytes()).decode('ascii')
    return f'data:{mime_type};base64,{encoded}'


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
        parts = [
            {
                'type': 'image_url',
                'image_url': {
                    'url': _image_to_data_url(image_path),
                },
            }
            for image_path in images
        ]
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

def _build_llama_payload(chat_arguments):
    arguments = dict(chat_arguments)
    think = arguments.pop('think', None)
    arguments.pop('options', None)
    arguments.pop('keep_alive', None)
    arguments.pop('model', None)
    messages = arguments.pop('messages', [])

    payload = {'model': LLAMA_API_MODEL, 'messages': [_message_to_dict(message) for message in messages], 'stream': bool(arguments.pop('stream', False))}
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

# BLOK BAŞLIĞI: LLAMA CHAT PAYLOAD - BİTİŞ

# BLOK BAŞLIĞI: LLAMA CHAT YANIT AYRIŞTIRMA - BAŞLANGIÇ

def _parse_llama_response(payload):
    choices = payload.get('choices') or []
    if not choices:
        error = payload.get('error')
        if isinstance(error, dict):
            detail = error.get('message') or str(error)
        else:
            detail = str(error or 'Llama boş yanıt döndürdü.')
        raise RuntimeError(detail)

    raw_message = choices[0].get('message') or {}
    tool_calls = []
    for item in raw_message.get('tool_calls') or []:
        function = item.get('function') or {}
        tool_calls.append(_LlamaToolCall(id=str(item.get('id') or ''), type=str(item.get('type') or 'function'), function=_LlamaToolFunction(name=str(function.get('name') or ''), arguments=_tool_arguments(function.get('arguments')))))

    usage = payload.get('usage') or {}
    timings = payload.get('timings') or {}
    prompt_tokens = int(usage.get('prompt_tokens') or 0)
    completion_tokens = int(usage.get('completion_tokens') or 0)
    if not prompt_tokens:
        prompt_tokens = int(timings.get('prompt_n') or 0) + int(timings.get('cache_n') or 0)
    if not completion_tokens:
        completion_tokens = int(timings.get('predicted_n') or 0)

    return _LlamaChatResponse(message=_LlamaMessage(role=str(raw_message.get('role') or 'assistant'), content=str(raw_message.get('content') or ''), tool_calls=tool_calls), prompt_eval_count=prompt_tokens, eval_count=completion_tokens)

# BLOK BAŞLIĞI: LLAMA CHAT YANIT AYRIŞTIRMA - BİTİŞ

# BLOK BAŞLIĞI: LLAMA CHAT ÇAĞRISI - BAŞLANGIÇ

def _llama_chat_worker(connection, chat_arguments):
    try:
        payload = _build_llama_payload(chat_arguments)
        request = Request(LLAMA_CHAT_URL, data=json.dumps(payload, ensure_ascii=False).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
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

def llama_chat(session, **kwargs):
    if session._stopping or session._cancel_requested.is_set():
        return _CANCELLED

    process_context = multiprocessing.get_context('spawn')
    receive_connection, send_connection = process_context.Pipe(duplex=False)
    process = process_context.Process(target=_llama_chat_worker, args=(send_connection, dict(kwargs)), daemon=True)
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
                    return _parse_llama_response(payload)
                if status == 'error':
                    raise RuntimeError(payload)
            if not process.is_alive():
                if receive_connection.poll(0.1):
                    continue
                raise RuntimeError(f'Llama istek süreci yanıt vermeden kapandı (çıkış kodu: {process.exitcode}).')
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

# BLOK BAŞLIĞI: LLAMA CHAT ÇAĞRISI - BİTİŞ
