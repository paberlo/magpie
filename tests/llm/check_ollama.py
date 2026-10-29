"""Checks magpie.utils.ollama against a fake Ollama server (run from the repository root)."""
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, '.')
from magpie.utils.ollama import ollama_generate, ollama_url

failures = 0


def check(name, cond):
    global failures
    print(('ok   ' if cond else 'FAIL ') + name)
    failures += not cond


check('host without port uses 11434', ollama_url('10.0.0.5') == 'http://10.0.0.5:11434/api/generate')
check('host with port keeps it', ollama_url('10.0.0.5:40123') == 'http://10.0.0.5:40123/api/generate')

state = {'fail_first': 2, 'calls': 0, 'payload': None}


class Fake(BaseHTTPRequestHandler):
    def do_POST(self):
        state['calls'] += 1
        state['payload'] = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if state['calls'] <= state['fail_first']:
            self.send_response(500)
            self.end_headers()
            return
        body = json.dumps({'response': 'Patch 1: x'}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


server = HTTPServer(('127.0.0.1', 0), Fake)
port = server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()

out = ollama_generate(f'127.0.0.1:{port}', 'qwen2.5-coder:7b', 'hello', waits=(0.1, 0.1, 0.1))
check('two server errors are retried, then the answer is returned', out == 'Patch 1: x' and state['calls'] == 3)
check('payload: model, prompt, no streaming, 32k context',
      state['payload'] == {'model': 'qwen2.5-coder:7b', 'prompt': 'hello', 'stream': False, 'options': {'num_ctx': 32768}})

state.update(fail_first=10, calls=0)
try:
    ollama_generate(f'127.0.0.1:{port}', 'm', 'p', waits=(0.1, 0.1))
    check('persistent errors raise RuntimeError', False)
except RuntimeError as e:
    check(f'persistent errors raise RuntimeError after 3 attempts ({state["calls"]} calls)', state['calls'] == 3)
server.shutdown()
server.server_close()  # free the port: connections are now refused

try:
    ollama_generate(f'127.0.0.1:{port}', 'm', 'p', waits=(0.1,))
    check('server down raises RuntimeError', False)
except RuntimeError as e:
    check('server down (connection refused) raises RuntimeError', 'unavailable' in str(e))

print('ALL OK' if failures == 0 else f'{failures} FAILURES')
