"""Safety and OBS v5 protocol tests; no live OBS or output operations."""
import importlib.util
import json
import base64
import hashlib
import socket
import struct
import threading
import time
import unittest
from unittest.mock import ANY, patch


class FakeSocket:
    def __init__(self, messages=None):
        self.messages = list(messages or [])
        self.sent = []
        self.closed = False
        self.timeouts = []

    def send(self, message):
        self.sent.append(json.loads(message))

    def recv(self):
        message = self.messages.pop(0)
        if isinstance(message, Exception):
            raise message
        return json.dumps(message)

    def settimeout(self, timeout):
        self.timeouts.append(timeout)

    def close(self, **kwargs):
        self.close_options = kwargs
        self.closed = True


class ClientTests(unittest.TestCase):
    def test_localhost_is_normalized_to_literal_loopback(self):
        from hands.obs_control import OBSControl, OBSControlError
        with patch('hands.obs_control._open_websocket', side_effect=OBSControlError('fixture')) as connect:
            with self.assertRaises(OBSControlError):
                OBSControl(host='localhost').execute('version')
        connect.assert_called_once_with('ws://127.0.0.1:4455', 5.0, deadline=ANY)

    def test_screenshot_rejects_dimensions_below_obs_minimum(self):
        from hands.obs_control import validate_action
        for size in (1, 7):
            with self.assertRaises(ValueError):
                validate_action('screenshot', {'sourceName': 'Scene', 'width': size, 'height': 360})

    def test_authenticated_version_request(self):
        import base64
        import hashlib
        from hands.obs_control import OBSControl
        sock = FakeSocket([
            {'op':0, 'd':{'rpcVersion':1, 'authentication':{'salt':'salt', 'challenge':'challenge'}}},
            {'op':2, 'd':{'negotiatedRpcVersion':1}},
            {'op':5, 'd':{}},
            {'op':7, 'd':{'requestType':'GetVersion', 'requestId':'req-id', 'requestStatus':{'result':True, 'code':100}, 'responseData':{'obsVersion':'32.2.2'}}},
        ])
        with patch('hands.obs_control._open_websocket', return_value=sock) as connect, patch('hands.obs_control.uuid.uuid4', return_value='req-id'):
            with OBSControl(password='password') as obs:
                self.assertEqual(obs.execute('version'), {'obsVersion':'32.2.2'})
        secret = base64.b64encode(hashlib.sha256(b'passwordsalt').digest()).decode()
        auth = base64.b64encode(hashlib.sha256((secret+'challenge').encode()).digest()).decode()
        self.assertEqual(sock.sent, [
            {'op':1, 'd':{'rpcVersion':1, 'eventSubscriptions':0, 'authentication':auth}},
            {'op':6, 'd':{'requestType':'GetVersion', 'requestId':'req-id', 'requestData':{}}},
        ])
        connect.assert_called_once_with('ws://127.0.0.1:4455', 5.0, deadline=ANY)
        self.assertTrue(sock.closed)

    def test_action_wire_shapes_and_aggregates(self):
        from hands.obs_control import OBSControl
        cases = [
            ('scenes', {}, [('GetSceneList', {})]),
            ('inputs', {}, [('GetInputList', {})]),
            ('status', {}, [('GetStreamStatus', {}), ('GetRecordStatus', {}), ('GetStats', {})]),
            ('scene-items', {'sceneName':'Live'}, [('GetSceneItemList', {'sceneName':'Live'})]),
            ('audio', {'inputName':'Mic'}, [('GetInputMute', {'inputName':'Mic'}), ('GetInputVolume', {'inputName':'Mic'})]),
            ('screenshot', {'sourceName':'Live','width':640,'height':360}, [('GetSourceScreenshot', {'sourceName':'Live','imageWidth':640,'imageHeight':360,'imageFormat':'png'})]),
            ('scene-create', {'sceneName':'Live'}, [('CreateScene', {'sceneName':'Live'})]),
            ('scene-switch', {'sceneName':'Live'}, [('SetCurrentProgramScene', {'sceneName':'Live'})]),
            ('scene-preview', {'sceneName':'Live'}, [('SetCurrentPreviewScene', {'sceneName':'Live'})]),
            ('source-visible', {'sceneName':'Live','sceneItemId':1,'sceneItemEnabled':False}, [('SetSceneItemEnabled', {'sceneName':'Live','sceneItemId':1,'sceneItemEnabled':False})]),
            ('input-mute', {'inputName':'Mic','inputMuted':True}, [('SetInputMute', {'inputName':'Mic','inputMuted':True})]),
            ('input-volume', {'inputName':'Mic','inputVolumeDb':-20}, [('SetInputVolume', {'inputName':'Mic','inputVolumeDb':-20})]),
            ('color-create', {'sceneName':'Live','inputName':'BG','color':123,'width':640,'height':360}, [('CreateInput', {'sceneName':'Live','inputName':'BG','inputKind':'color_source_v3','inputSettings':{'color':123,'width':640,'height':360},'sceneItemEnabled':True})]),
            ('studio-mode', {'studioModeEnabled':True}, [('SetStudioModeEnabled', {'studioModeEnabled':True})]),
            ('stream-start', {}, [('StartStream', {})]), ('stream-stop', {}, [('StopStream', {})]),
            ('record-start', {}, [('StartRecord', {})]), ('record-stop', {}, [('StopRecord', {})]),
        ]
        for action, data, requests in cases:
            with self.subTest(action=action):
                responses = [{'op':7,'d':{'requestType':name,'requestId':'id','requestStatus':{'result':True,'code':100},'responseData':{'value':i}}} for i,(name,_) in enumerate(requests)]
                sock = FakeSocket([{'op':0,'d':{'rpcVersion':1}}, {'op':2,'d':{'negotiatedRpcVersion':1}}, *responses])
                with patch('hands.obs_control._open_websocket', return_value=sock), patch('hands.obs_control.uuid.uuid4', return_value='id'):
                    with OBSControl() as obs:
                        result = obs.execute(action, data, allow_write=True, allow_output=True)
                self.assertEqual([(m['d']['requestType'], m['d']['requestData']) for m in sock.sent[1:]], requests)
                if action == 'status':
                    self.assertEqual(result, {'stream':{'value':0}, 'record':{'value':1}, 'stats':{'value':2}})
                elif action == 'audio':
                    self.assertEqual(result, {'mute':{'value':0}, 'volume':{'value':1}})
                else:
                    self.assertEqual(result, {'value':0})

    def test_text_set_only_existing_text_sources(self):
        from hands.obs_control import OBSControl, OBSControlError
        for kind in ('text_ft2_source', 'text_ft2_source_v2', 'text_gdiplus', 'text_gdiplus_v2', 'browser_source', None):
            with self.subTest(kind=kind):
                inputs = [] if kind is None else [{'inputName':'Title', 'inputKind':kind}]
                sock = FakeSocket([
                    {'op':0,'d':{'rpcVersion':1}}, {'op':2,'d':{'negotiatedRpcVersion':1}},
                    {'op':7,'d':{'requestType':'GetInputList','requestId':'id','requestStatus':{'result':True},'responseData':{'inputs':inputs}}},
                    {'op':7,'d':{'requestType':'SetInputSettings','requestId':'id','requestStatus':{'result':True},'responseData':{}}},
                ])
                with patch('hands.obs_control._open_websocket', return_value=sock), patch('hands.obs_control.uuid.uuid4', return_value='id'):
                    with OBSControl() as obs:
                        if kind in ('browser_source', None):
                            with self.assertRaises(OBSControlError):
                                obs.execute('text-set', {'inputName':'Title','text':'DJ'}, allow_write=True)
                            self.assertEqual(len(sock.sent), 2)
                        else:
                            self.assertEqual(obs.execute('text-set', {'inputName':'Title','text':'DJ'}, allow_write=True), {})
                            self.assertEqual(sock.sent[-1]['d']['requestData'], {'inputName':'Title','inputSettings':{'text':'DJ'},'overlay':True})

    def test_protocol_failures_are_sanitized_and_close_without_retry(self):
        from hands.obs_control import OBSControl, OBSControlError
        hello = {'op':0,'d':{'rpcVersion':1}}
        identified = {'op':2,'d':{'negotiatedRpcVersion':1}}
        reply = {'op':7,'d':{'requestType':'StartRecord','requestId':'id','requestStatus':{'result':True},'responseData':{}}}
        bad_reply = json.loads(json.dumps(reply))
        bad_reply['d']['requestStatus'] = {'result':False,'code':500,'comment':'secret-server-settings'}
        mismatch = json.loads(json.dumps(reply))
        mismatch['d']['requestId'] = 'wrong'
        bad_data = json.loads(json.dumps(reply))
        bad_data['d']['responseData'] = ['secret']
        for tail in (bad_reply, mismatch, bad_data, RuntimeError('secret-password'), {'op':8,'d':{}}, {'op':True,'d':{}}):
            with self.subTest(tail=tail):
                sock = FakeSocket([hello, identified, tail])
                with patch('hands.obs_control._open_websocket', return_value=sock) as connect, patch('hands.obs_control.uuid.uuid4', return_value='id'):
                    obs = OBSControl(password='secret-password')
                    with self.assertRaises(OBSControlError) as raised:
                        obs.execute('record-start', allow_write=True, allow_output=True)
                    self.assertNotIn('secret', str(raised.exception))
                    self.assertTrue(sock.closed)
                    self.assertEqual(len(sock.sent), 2)
                    with self.assertRaises(OBSControlError):
                        obs.execute('record-start', allow_write=True, allow_output=True)
                    connect.assert_called_once()
        for messages in ([{'op':2,'d':{}}],
                         [{'op':0,'d':{'rpcVersion':0}}, identified],
                         [{'op':0,'d':{'rpcVersion':1,'authentication':{'salt':'salt','challenge':'challenge'}}}],
                         [hello, {'op':2,'d':{'negotiatedRpcVersion':2}}]):
            with self.subTest(handshake=messages):
                sock = FakeSocket(messages)
                with patch('hands.obs_control._open_websocket', return_value=sock):
                    with self.assertRaises(OBSControlError):
                        OBSControl().execute('version')
                self.assertTrue(sock.closed)

    def test_message_size_and_total_deadline(self):
        from hands.obs_control import OBSControl, OBSControlError
        sock = FakeSocket([{'op':0,'d':{'rpcVersion':1}}, {'op':2,'d':{'negotiatedRpcVersion':1}},
                           {'op':5,'d':{'padding':'x' * (16 * 1024 * 1024)}}])
        with patch('hands.obs_control._open_websocket', return_value=sock):
            with self.assertRaisesRegex(OBSControlError, 'size'):
                OBSControl().execute('version')
        self.assertTrue(sock.closed)
        sock = FakeSocket([{'op':0,'d':{'rpcVersion':1}}, {'op':2,'d':{'negotiatedRpcVersion':1}}, {'op':5,'d':{}}])
        with patch('hands.obs_control._open_websocket', return_value=sock), patch('hands.obs_control.time.monotonic', side_effect=[0, 0, 0, 0, 0, 0, 6]):
            with self.assertRaisesRegex(OBSControlError, 'timed out'):
                OBSControl().execute('version')
        self.assertTrue(sock.closed)
        self.assertTrue(all(0 < t <= 5 for t in sock.timeouts))

    def test_close_does_not_wait_for_peer_acknowledgement(self):
        from hands.obs_control import OBSControl
        sock = FakeSocket([{'op':0,'d':{'rpcVersion':1}}, {'op':2,'d':{'negotiatedRpcVersion':1}},
                           {'op':7,'d':{'requestType':'GetVersion','requestId':'id','requestStatus':{'result':True},'responseData':{}}}])
        with patch('hands.obs_control._open_websocket', return_value=sock), patch('hands.obs_control.uuid.uuid4', return_value='id'):
            with OBSControl() as obs:
                obs.execute('version')
        self.assertEqual(sock.close_options, {'timeout':0})
        obs.close()

    def test_transport_bypasses_proxies_and_redirects(self):
        from hands.obs_control import _open_websocket
        with patch('websocket.create_connection') as connect, patch('hands.obs_control.socket.socket') as raw_socket:
            _open_websocket('ws://127.0.0.1:4455', 5.0)
        raw_socket.return_value.connect.assert_called_once_with(('127.0.0.1', 4455))
        self.assertIs(connect.call_args.kwargs['socket']._sock, raw_socket.return_value)
        self.assertEqual(connect.call_args.kwargs['redirect_limit'], 0)
        self.assertEqual(connect.call_args.kwargs['http_no_proxy'], ['127.0.0.1', '::1', 'localhost'])

    def test_low_level_connect_recv_and_partial_sends_share_deadline(self):
        from hands.obs_control import _DeadlineSocket, OBSControlError
        with patch('hands.obs_control.socket.socket') as factory:
            raw = factory.return_value
            raw.send.return_value = 1  # websocket-client may loop on partial sends.
            transport = _DeadlineSocket(raw, deadline=1)
            transport.settimeout(5)  # Cannot extend the absolute deadline.
            with patch('hands.obs_control.time.monotonic', side_effect=[0, .1, .2, .3, .4, .5, .6, .7, 1]):
                transport.connect(('127.0.0.1', 12345))
                transport.recv(1)
                transport.send(b'ab')
                transport.send(b'b')
                with self.assertRaisesRegex(OBSControlError, 'timed out'):
                    transport.send(b'late')
            self.assertEqual([call.args[0] for call in raw.settimeout.call_args_list], [1, .8, .6, .4])
            self.assertEqual(raw.send.call_count, 2)

    def test_failed_connect_or_upgrade_releases_preconnected_socket(self):
        from hands.obs_control import OBSControl, OBSControlError
        for phase in ('connect', 'upgrade'):
            with self.subTest(phase=phase), patch('hands.obs_control.socket.socket') as factory, \
                    patch('websocket.create_connection') as upgrade:
                raw = factory.return_value
                failing = raw.connect if phase == 'connect' else upgrade
                failing.side_effect = RuntimeError('synthetic-secret')
                obs = OBSControl()
                with self.assertRaisesRegex(OBSControlError, '^OBS communication failed$'):
                    obs.execute('version')
                raw.close.assert_called_once()
                self.assertTrue(obs._closed)
                self.assertIsNone(obs._socket)
                if phase == 'connect':
                    upgrade.assert_not_called()
                else:
                    upgrade.assert_called_once()

    def test_identified_rpc_version_cannot_be_boolean(self):
        from hands.obs_control import OBSControl, OBSControlError
        sock = FakeSocket([{'op':0,'d':{'rpcVersion':1}}, {'op':2,'d':{'negotiatedRpcVersion':True}},
                           {'op':7,'d':{'requestType':'GetVersion','requestId':'id','requestStatus':{'result':True},'responseData':{}}}])
        with patch('hands.obs_control._open_websocket', return_value=sock), patch('hands.obs_control.uuid.uuid4', return_value='id'):
            with self.assertRaises(OBSControlError):
                OBSControl().execute('version')
        self.assertEqual(len(sock.sent), 1)
        self.assertTrue(sock.closed)

    def test_local_only_lazy_construction_and_gates(self):
        from hands.obs_control import OBSControl
        for kwargs in ({'host':'example.com'}, {'host':'127.0.0.2'}, {'port':True},
                       {'port':0}, {'port':65536}, {'timeout_s':0},
                       {'timeout_s':float('inf')}, {'timeout_s':True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                OBSControl(**kwargs)
        with patch('hands.obs_control._open_websocket') as connect:
            for host in ('127.0.0.1', '::1', 'localhost'):
                with OBSControl(host=host, password='hidden-secret') as obs:
                    self.assertNotIn('hidden-secret', repr(obs))
                    with self.assertRaises(PermissionError):
                        obs.execute('stream-start')
                    with self.assertRaises(ValueError):
                        obs.execute('raw')
                obs.close()
            connect.assert_not_called()


class LocalWebSocketServer:
    """Tiny real RFC6455 peer; only stdlib, ephemeral loopback port."""
    def __init__(self, mode='normal'):
        self.mode = mode
        self.received = []
        self.errors = []
        self.listener = socket.socket()
        self.listener.bind(('127.0.0.1', 0))
        self.listener.listen(1)
        self.listener.settimeout(3)
        self.port = self.listener.getsockname()[1]
        self.thread = threading.Thread(target=self.serve, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.thread.join(4)
        self.listener.close()
        if self.thread.is_alive():
            raise AssertionError('fake server failed to finish')
        if self.errors:
            raise AssertionError(self.errors)

    @staticmethod
    def exact(conn, n):
        result = b''
        while len(result) < n:
            chunk = conn.recv(n - len(result))
            if not chunk:
                raise EOFError
            result += chunk
        return result

    def read(self, conn):
        first, second = self.exact(conn, 2)
        if first & 15 == 8:
            return None
        if first & 15 != 1 or not second & 128:
            raise AssertionError('client frame must be masked text')
        length = second & 127
        if length == 126:
            length = struct.unpack('!H', self.exact(conn, 2))[0]
        elif length == 127:
            length = struct.unpack('!Q', self.exact(conn, 8))[0]
        mask = self.exact(conn, 4)
        raw = self.exact(conn, length)
        message = json.loads(bytes(b ^ mask[i % 4] for i,b in enumerate(raw)))
        self.received.append(message)
        return message

    @staticmethod
    def send(conn, message):
        raw = json.dumps(message).encode()
        header = bytes([129, len(raw)]) if len(raw) < 126 else bytes([129, 126]) + struct.pack('!H', len(raw))
        conn.sendall(header + raw)

    def serve(self):
        try:
            conn, _ = self.listener.accept()
            with conn:
                conn.settimeout(3)
                request = b''
                while not request.endswith(b'\r\n\r\n'):
                    request += self.exact(conn, 1)
                headers = dict(line.split(': ',1) for line in request.decode().split('\r\n')[1:] if ': ' in line)
                key = headers['Sec-WebSocket-Key']
                accept = base64.b64encode(hashlib.sha1((key+'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode()
                upgrade = ('HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: '+accept+'\r\n\r\n').encode()
                if self.mode == 'slow-http':
                    for offset in range(0, len(upgrade), 8):
                        conn.sendall(upgrade[offset:offset + 8])
                        time.sleep(.05)
                    return
                conn.sendall(upgrade)
                self.send(conn, {'op':0,'d':{'rpcVersion':1,'authentication':{'salt':'local-salt','challenge':'local-challenge'}}})
                self.read(conn)
                self.send(conn, {'op':2,'d':{'negotiatedRpcVersion':1}})
                while True:
                    message = self.read(conn)
                    if message is None:
                        break
                    d = message['d']
                    if self.mode == 'events':
                        for _ in range(30):
                            self.send(conn, {'op':5,'d':{'eventType':'Ignored'}})
                            time.sleep(.01)
                        break
                    if self.mode == 'fragments' and len(self.received) == 3:
                        # One OBS message spread over continuation frames; every
                        # byte arrives faster than the nominal socket timeout.
                        raw = json.dumps({'op':7,'d':{'requestType':d['requestType'],
                            'requestId':d['requestId'],'requestStatus':{'result':True},
                            'responseData':{}}}).encode()
                        for offset in range(0, len(raw), 16):
                            part = raw[offset:offset + 16]
                            first = (128 if offset + 16 >= len(raw) else 0) | (1 if offset == 0 else 0)
                            for byte in bytes([first, len(part)]) + part:
                                conn.sendall(bytes([byte]))
                                time.sleep(.01)
                        continue
                    self.send(conn, {'op':5,'d':{'eventType':'Ignored'}})
                    self.send(conn, {'op':7,'d':{'requestType':d['requestType'], 'requestId':d['requestId'] if self.mode != 'mismatch' else 'wrong', 'requestStatus':{'result':self.mode != 'failure','code':100 if self.mode != 'failure' else 500,'comment':'never-report-this-secret'}, 'responseData':{'obsVersion':'fake-local'}}})
        except (BrokenPipeError, ConnectionResetError, EOFError):
            pass  # expected when client closes after timeout/protocol failure
        except Exception as exc:
            self.errors.append(repr(exc))


class RealTransportTests(unittest.TestCase):
    def test_slow_http_upgrade_has_total_deadline(self):
        from hands.obs_control import OBSControl, OBSControlError
        with LocalWebSocketServer('slow-http') as server:
            obs = OBSControl(port=server.port, timeout_s=.2)
            start = time.monotonic()
            with self.assertRaises(OBSControlError):
                obs.execute('version')
            self.assertLess(time.monotonic() - start, .5)
            self.assertTrue(obs._closed)
            self.assertIsNone(obs._socket)
            self.assertEqual(server.received, [])

    def test_trickling_fragments_on_reused_client_have_total_deadline(self):
        from hands.obs_control import OBSControl, OBSControlError
        with LocalWebSocketServer('fragments') as server:
            with OBSControl(port=server.port, password='test-only', timeout_s=.2) as obs:
                self.assertEqual(obs.execute('version'), {'obsVersion':'fake-local'})
                time.sleep(.25)  # The next execute must get a fresh budget.
                start = time.monotonic()
                with self.assertRaises(OBSControlError):
                    obs.execute('version')
                self.assertLess(time.monotonic() - start, .5)
                self.assertTrue(obs._closed)
                self.assertIsNone(obs._socket)
                with self.assertRaisesRegex(OBSControlError, 'closed'):
                    obs.execute('version')
            self.assertEqual(len(server.received), 3)  # Identify + two requests, no retry.

    def test_real_websocket_auth_request_ids_reuse_and_events(self):
        from hands.obs_control import OBSControl
        with LocalWebSocketServer() as server:
            with OBSControl(port=server.port, password='test-only') as obs:
                self.assertEqual(obs.execute('version'), {'obsVersion':'fake-local'})
                self.assertEqual(obs.execute('version'), {'obsVersion':'fake-local'})
        secret = base64.b64encode(hashlib.sha256(b'test-onlylocal-salt').digest()).decode()
        expected = base64.b64encode(hashlib.sha256((secret+'local-challenge').encode()).digest()).decode()
        self.assertEqual(server.received[0], {'op':1,'d':{'rpcVersion':1,'eventSubscriptions':0,'authentication':expected}})
        requests = server.received[1:]
        self.assertEqual(len(requests), 2)
        self.assertNotEqual(requests[0]['d']['requestId'], requests[1]['d']['requestId'])
        for message in requests:
            self.assertEqual(message['op'], 6)
            self.assertEqual(message['d']['requestType'], 'GetVersion')
            self.assertEqual(message['d']['requestData'], {})

    def test_real_transport_failure_mismatch_and_event_deadline(self):
        from hands.obs_control import OBSControl, OBSControlError
        for mode in ('failure','mismatch','events'):
            with self.subTest(mode=mode), LocalWebSocketServer(mode) as server:
                with OBSControl(port=server.port, password='test-only', timeout_s=.15) as obs:
                    start = time.monotonic()
                    with self.assertRaises(OBSControlError) as error:
                        obs.execute('version')
                    self.assertNotIn('secret', str(error.exception))
                    self.assertLess(time.monotonic() - start, 1)
                self.assertEqual(len(server.received), 2)


class ValidationTests(unittest.TestCase):
    def test_read_validation_is_available_without_transport(self):
        self.assertIsNotNone(importlib.util.find_spec('hands.obs_control'))
        from hands.obs_control import validate_action
        self.assertEqual(validate_action('version'), {})

    def test_strict_schemas_and_permissions(self):
        from hands.obs_control import validate_action
        cases = {
            'version': {}, 'scenes': {}, 'inputs': {}, 'status': {},
            'scene-items': {'sceneName': 'Live'},
            'audio': {'inputName': 'Mic'},
            'screenshot': {'sourceName': 'Live', 'width': 1280, 'height': 720},
            'scene-create': {'sceneName': 'Live'},
            'scene-switch': {'sceneName': 'Live'},
            'scene-preview': {'sceneName': 'Live'},
            'source-visible': {'sceneName': 'Live', 'sceneItemId': 0, 'sceneItemEnabled': True},
            'input-mute': {'inputName': 'Mic', 'inputMuted': False},
            'input-volume': {'inputName': 'Mic', 'inputVolumeDb': -12.5},
            'text-set': {'inputName': 'Title', 'text': ''},
            'color-create': {'sceneName': 'Live', 'inputName': 'BG', 'color': 4278190335, 'width': 1920, 'height': 1080},
            'studio-mode': {'studioModeEnabled': True},
            'stream-start': {}, 'stream-stop': {}, 'record-start': {}, 'record-stop': {},
        }
        reads = {'version', 'scenes', 'inputs', 'status', 'scene-items', 'audio', 'screenshot'}
        outputs = {'stream-start', 'stream-stop', 'record-start', 'record-stop'}
        for action, data in cases.items():
            with self.subTest(action=action):
                self.assertEqual(validate_action(action, data, allow_write=True, allow_output=True), data)
                if action not in reads:
                    with self.assertRaises(PermissionError):
                        validate_action(action, data)
                if action in outputs:
                    with self.assertRaises(PermissionError):
                        validate_action(action, data, allow_write=True)
                with self.assertRaises(ValueError):
                    validate_action(action, dict(data, unexpected='secret'), allow_write=True, allow_output=True)
                for key in data:
                    with self.assertRaises(ValueError):
                        validate_action(action, {k:v for k,v in data.items() if k != key}, allow_write=True, allow_output=True)
        bad = [('raw', {}), ('version', []), ('input-mute', {'inputName':'Mic', 'inputMuted':1}),
               ('input-volume', {'inputName':'Mic', 'inputVolumeDb':float('nan')}),
               ('input-volume', {'inputName':'Mic', 'inputVolumeDb':1}),
               ('input-volume', {'inputName':'Mic', 'inputVolumeDb':-101}),
               ('scene-items', {'sceneName':' '}),
               ('screenshot', {'sourceName':'Live','width':True,'height':720}),
               ('color-create', {'sceneName':'Live','inputName':'BG','color':-1,'width':1,'height':1})]
        for action, data in bad:
            with self.subTest(bad=action, data=data), self.assertRaises(ValueError):
                validate_action(action, data, allow_write=True, allow_output=True)
        with self.assertRaises(ValueError):
            validate_action('version', allow_write=1)


if __name__ == '__main__':
    unittest.main()
