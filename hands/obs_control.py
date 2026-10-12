"""Harness-neutral localhost OBS WebSocket v5 control.

No connection is made until a validated execute(). websocket-client is optional
until that point. This module deliberately exposes no arbitrary RPC surface.
"""
from __future__ import annotations

import math
import uuid
import json
import time
import hashlib
import base64
import socket
from urllib.parse import urlsplit

READ_ACTIONS = frozenset({'version', 'scenes', 'inputs', 'status', 'scene-items', 'audio', 'screenshot'})
WRITE_ACTIONS = frozenset({'scene-create', 'scene-switch', 'scene-preview', 'source-visible', 'input-mute', 'input-volume', 'text-set', 'color-create', 'studio-mode'})
OUTPUT_ACTIONS = frozenset({'stream-start', 'stream-stop', 'record-start', 'record-stop'})
_SCHEMA = {
    'version': {}, 'scenes': {}, 'inputs': {}, 'status': {},
    'scene-items': {'sceneName': 'name'}, 'audio': {'inputName': 'name'},
    'screenshot': {'sourceName': 'name', 'width': 'dimension', 'height': 'dimension'},
    'scene-create': {'sceneName': 'name'}, 'scene-switch': {'sceneName': 'name'},
    'scene-preview': {'sceneName': 'name'},
    'source-visible': {'sceneName': 'name', 'sceneItemId': 'id', 'sceneItemEnabled': 'bool'},
    'input-mute': {'inputName': 'name', 'inputMuted': 'bool'},
    'input-volume': {'inputName': 'name', 'inputVolumeDb': 'volume'},
    'text-set': {'inputName': 'name', 'text': 'text'},
    'color-create': {'sceneName': 'name', 'inputName': 'name', 'color': 'color', 'width': 'dimension', 'height': 'dimension'},
    'studio-mode': {'studioModeEnabled': 'bool'},
    **{action: {} for action in OUTPUT_ACTIONS},
}


def validate_action(action: str, data: dict | None = None, *, allow_write: bool = False, allow_output: bool = False) -> dict:
    """Return a validated copy; raise ValueError/PermissionError without I/O.

    All schema fields are required. Dimensions are 1..4096 (screenshots 8..4096), color is an OBS
    unsigned 32-bit ABGR integer, volume is -100..0 dB. Permissions are bools.
    """
    if type(allow_write) is not bool or type(allow_output) is not bool:
        raise ValueError('OBS permission flags must be boolean')
    if not isinstance(action, str) or action not in _SCHEMA:
        raise ValueError('Unsupported OBS action')
    if action in WRITE_ACTIONS | OUTPUT_ACTIONS and not allow_write:
        raise PermissionError('OBS action requires allow_write')
    if action in OUTPUT_ACTIONS and not allow_output:
        raise PermissionError('OBS output action requires allow_output')
    data = {} if data is None else data
    if type(data) is not dict or data.keys() != _SCHEMA[action].keys():
        raise ValueError('Invalid OBS action fields')
    for key, kind in _SCHEMA[action].items():
        v = data[key]
        valid = False
        if kind == 'name':
            valid = isinstance(v, str) and bool(v.strip()) and len(v) <= 1024 and '\x00' not in v
        elif kind == 'text':
            valid = isinstance(v, str) and len(v) <= 65536 and '\x00' not in v
        elif kind == 'bool':
            valid = type(v) is bool
        elif kind == 'volume':
            valid = type(v) in (int, float) and -100 <= v <= 0 and math.isfinite(v)
        elif kind in ('id', 'dimension', 'color'):
            low, high = {'id': (0, 2**31-1), 'dimension': (1, 4096), 'color': (0, 2**32-1)}[kind]
            valid = type(v) is int and low <= v <= high
        if not valid:
            raise ValueError('Invalid OBS action value')
        if action == 'screenshot' and kind == 'dimension' and isinstance(v, int) and v < 8:
            raise ValueError('OBS screenshot dimensions must be at least 8')
    return dict(data)


class _DeadlineSocket:
    """Rebudget every low-level I/O, including websocket-client's inner loops."""

    def __init__(self, sock, deadline):
        self._sock = sock
        self.deadline = deadline
        self._timeout = None

    def gettimeout(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise OBSControlError('OBS operation timed out')
        return remaining if self._timeout is None else min(remaining, self._timeout)

    def settimeout(self, timeout):
        # websocket-client may change its per-read timeout, never our deadline.
        self._timeout = timeout

    def _io(self, method, *args):
        self._sock.settimeout(self.gettimeout())
        result = method(*args)
        self.gettimeout()  # Do not accept success after expiry.
        return result

    def connect(self, address):
        return self._io(self._sock.connect, address)

    def recv(self, size):
        return self._io(self._sock.recv, size)

    def send(self, data):
        return self._io(self._sock.send, data)

    def __getattr__(self, name):
        return getattr(self._sock, name)


def _open_websocket(url, timeout, *, deadline=None):
    # Lazy import lets CLI validation/help work without the optional dependency.
    import websocket
    deadline = time.monotonic() + timeout if deadline is None else deadline
    endpoint = urlsplit(url)
    host = endpoint.hostname
    # Preconnect literal loopback; supplied sockets bypass proxy/DNS machinery.
    if endpoint.scheme != 'ws' or host not in ('127.0.0.1', '::1'):
        raise ValueError('OBS host must be literal loopback')
    raw = socket.socket(socket.AF_INET6 if host == '::1' else socket.AF_INET, socket.SOCK_STREAM)
    transport = _DeadlineSocket(raw, deadline)
    try:
        transport.connect((host, endpoint.port))
        return websocket.create_connection(url, socket=transport, timeout=transport.gettimeout(),
                                           redirect_limit=0,
                                           http_no_proxy=['127.0.0.1', '::1', 'localhost'])
    except Exception:
        raw.close()
        raise


class OBSControlError(RuntimeError):
    """Sanitized protocol/transport failure; never contains server comments."""


class OBSControl:
    """Single-owner synchronous client. close() is terminal; no auto-retries."""

    def __init__(self, host='127.0.0.1', port=4455, password=None, timeout_s=5.0):
        if host not in ('127.0.0.1', '::1', 'localhost'):
            raise ValueError('OBS host must be literal loopback or localhost')
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError('Invalid OBS port')
        if type(timeout_s) not in (int, float) or not 0 < timeout_s <= 300 or not math.isfinite(timeout_s):
            raise ValueError('Invalid OBS timeout')
        if password is not None and not isinstance(password, str):
            raise ValueError('Invalid OBS password type')
        self._host, self._port = ('127.0.0.1' if host == 'localhost' else host), port
        self._password, self._timeout_s = password, timeout_s
        self._socket = None
        self._closed = False

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

    def close(self):
        sock, self._socket = self._socket, None
        self._closed = True
        self._password = None
        if sock is not None:
            try:
                # Peer acknowledgement must not extend an operation deadline.
                if isinstance(getattr(sock, 'sock', None), _DeadlineSocket):
                    # No close-frame send or peer wait can consume extra budget.
                    sock.shutdown()
                else:
                    sock.close(timeout=0)
            except Exception:
                pass

    def _receive(self, deadline):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise OBSControlError('OBS operation timed out')
        self._socket.settimeout(remaining)
        raw = self._socket.recv()
        if not isinstance(raw, (str, bytes)) or len(raw) > 16 * 1024 * 1024:
            raise OBSControlError('OBS message size exceeded')
        message = json.loads(raw)
        if type(message) is not dict or type(message.get('op')) is not int or type(message.get('d')) is not dict:
            raise OBSControlError('Invalid OBS message')
        if time.monotonic() >= deadline:
            raise OBSControlError('OBS operation timed out')
        return message

    def _send(self, message, deadline):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise OBSControlError('OBS operation timed out')
        self._socket.settimeout(remaining)
        self._socket.send(json.dumps(message))

    def _connect(self, deadline):
        if self._closed:
            raise OBSControlError('OBS client is closed')
        if self._socket is not None:
            transport = getattr(self._socket, 'sock', None)
            if isinstance(transport, _DeadlineSocket):
                transport.deadline = deadline
            return
        host = '[::1]' if self._host == '::1' else self._host
        self._socket = _open_websocket(f'ws://{host}:{self._port}', self._timeout_s, deadline=deadline)
        hello = self._receive(deadline)
        if hello['op'] != 0 or type(hello['d'].get('rpcVersion')) is not int or hello['d']['rpcVersion'] < 1:
            raise OBSControlError('Invalid OBS Hello')
        identify = {'rpcVersion':1, 'eventSubscriptions':0}
        if 'authentication' in hello['d']:
            auth = hello['d']['authentication']
            if self._password is None:
                raise OBSControlError('OBS authentication requires a password')
            secret = base64.b64encode(hashlib.sha256((self._password + auth['salt']).encode()).digest()).decode()
            identify['authentication'] = base64.b64encode(hashlib.sha256((secret + auth['challenge']).encode()).digest()).decode()
        self._send({'op':1, 'd':identify}, deadline)
        identified = self._receive(deadline)
        if (identified['op'] != 2 or type(identified['d'].get('negotiatedRpcVersion')) is not int
                or identified['d']['negotiatedRpcVersion'] != 1):
            raise OBSControlError('OBS identification failed')

    def _request(self, request_type, data, deadline):
        request_id = str(uuid.uuid4())
        self._send({'op':6, 'd':{'requestType':request_type, 'requestId':request_id, 'requestData':data}}, deadline)
        while True:
            message = self._receive(deadline)
            if message['op'] == 5:
                continue
            d = message['d']
            if message['op'] != 7 or d.get('requestId') != request_id or d.get('requestType') != request_type:
                raise OBSControlError('Unexpected OBS response')
            if d['requestStatus'].get('result') is not True:
                raise OBSControlError('OBS request failed')
            response = d.get('responseData', {})
            if type(response) is not dict:
                raise OBSControlError('Invalid OBS response data')
            return response

    def execute(self, action: str, data: dict | None = None, *, allow_write=False, allow_output=False) -> dict:
        payload = validate_action(action, data, allow_write=allow_write, allow_output=allow_output)
        deadline = time.monotonic() + self._timeout_s
        try:
            self._connect(deadline)
            if action == 'status':
                return {key: self._request(rpc, {}, deadline) for key, rpc in (
                    ('stream', 'GetStreamStatus'), ('record', 'GetRecordStatus'), ('stats', 'GetStats'))}
            if action == 'audio':
                return {key: self._request(rpc, payload, deadline) for key, rpc in (
                    ('mute', 'GetInputMute'), ('volume', 'GetInputVolume'))}
            if action == 'screenshot':
                return self._request('GetSourceScreenshot', {
                    'sourceName':payload['sourceName'], 'imageWidth':payload['width'],
                    'imageHeight':payload['height'], 'imageFormat':'png'}, deadline)
            if action == 'text-set':
                inputs = self._request('GetInputList', {}, deadline).get('inputs', [])
                allowed = {'text_ft2_source', 'text_ft2_source_v2', 'text_gdiplus', 'text_gdiplus_v2'}
                if not any(item.get('inputName') == payload['inputName'] and item.get('inputKind') in allowed for item in inputs):
                    raise OBSControlError('OBS input is not a supported text source')
                return self._request('SetInputSettings', {
                    'inputName':payload['inputName'], 'inputSettings':{'text':payload['text']}, 'overlay':True}, deadline)
            if action == 'color-create':
                return self._request('CreateInput', {
                    'sceneName':payload['sceneName'], 'inputName':payload['inputName'],
                    'inputKind':'color_source_v3', 'sceneItemEnabled':True,
                    'inputSettings':{key:payload[key] for key in ('color', 'width', 'height')}}, deadline)
            rpc = {
                'version':'GetVersion', 'scenes':'GetSceneList', 'inputs':'GetInputList',
                'scene-items':'GetSceneItemList', 'scene-create':'CreateScene',
                'scene-switch':'SetCurrentProgramScene', 'scene-preview':'SetCurrentPreviewScene',
                'source-visible':'SetSceneItemEnabled', 'input-mute':'SetInputMute',
                'input-volume':'SetInputVolume', 'studio-mode':'SetStudioModeEnabled',
                'stream-start':'StartStream', 'stream-stop':'StopStream',
                'record-start':'StartRecord', 'record-stop':'StopRecord',
            }[action]
            return self._request(rpc, payload, deadline)
        except Exception as exc:
            self.close()
            if isinstance(exc, OBSControlError):
                raise exc from None
            raise OBSControlError('OBS communication failed') from None
