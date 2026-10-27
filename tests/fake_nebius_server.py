"""A local no-network OpenAI-compatible server used to test real mode.

It speaks the same wire protocol as Nebius Token Factory for the two endpoints
Forge uses (``GET /v1/models`` and ``POST /v1/chat/completions``), including
``tool_calls`` and ``role: tool`` messages. That lets the unit tests exercise
the *entire* HTTP path of real mode on a machine with no Nebius key.

This file is a test fixture. It is never used by the app at runtime.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from forge.llm import MockBackend  # noqa: E402
from forge.config import DEFAULT_MODEL, Config  # noqa: E402

EXPECTED_KEY = "test-key-not-real"


class Handler(BaseHTTPRequestHandler):
    server_version = "FakeNebius/1.0"

    # ---------------------------------------------------------------- helpers
    def _send(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):  # silence request logging in tests
        pass

    def _authorised(self):
        auth = self.headers.get("Authorization", "")
        self.server.seen_auth.append(auth)
        return auth == "Bearer %s" % EXPECTED_KEY

    # ---------------------------------------------------------------- routes
    def do_GET(self):
        if self.path.rstrip("/") == "/v1/models":
            if not self._authorised():
                self._send(401, {"error": {"message": "invalid api key"}})
                return
            self.server.model_lists += 1
            self._send(
                200,
                {
                    "object": "list",
                    "data": [{"id": DEFAULT_MODEL, "object": "model"}, {"id": "other/model"}],
                },
            )
            return
        self._send(404, {"error": {"message": "not found: %s" % self.path}})

    def do_POST(self):
        if self.path.rstrip("/") != "/v1/chat/completions":
            self._send(404, {"error": {"message": "not found: %s" % self.path}})
            return
        if not self._authorised():
            self._send(401, {"error": {"message": "invalid api key"}})
            return
        length = int(self.headers.get("Content-Length") or 0)
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            self._send(400, {"error": {"message": "bad json"}})
            return

        self.server.requests.append(payload)
        mock = self.server.mock
        message = mock.complete(payload.get("messages", []), payload.get("tools", []))
        # echo back what a real OpenAI-compatible server returns
        self._send(
            200,
            {
                "id": "chatcmpl-fake-%d" % len(self.server.requests),
                "object": "chat.completion",
                "model": payload.get("model", DEFAULT_MODEL),
                "choices": [{"index": 0, "message": message, "finish_reason": "tool_calls"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
            },
        )


class FakeNebiusServer:
    """Context manager wrapping a ThreadingHTTPServer on an ephemeral port."""

    def __init__(self, key=EXPECTED_KEY):
        self.key = key
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.httpd.requests = []
        self.httpd.seen_auth = []
        self.httpd.model_lists = 0
        # Default script so a plain `python -m forge --real` against this server
        # works even without calling config() first.
        self.httpd.mock = MockBackend(Config(goal="demo", mode="mock"))
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    @property
    def port(self):
        return self.httpd.server_address[1]

    @property
    def base_url(self):
        return "http://127.0.0.1:%d/v1" % self.port

    @property
    def requests(self):
        return self.httpd.requests

    @property
    def seen_auth(self):
        return self.httpd.seen_auth

    @property
    def model_lists(self):
        return self.httpd.model_lists

    def config(self, **kw):
        params = dict(
            goal="Build a temperature converter with tests",
            mode="real",
            api_key=self.key,
            base_url=self.base_url,
            model=DEFAULT_MODEL,
            out_dir="build",
        )
        params.update(kw)
        self.httpd.mock = MockBackend(Config(goal=params["goal"], mode="mock"))
        return Config(**params)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)
        return False


if __name__ == "__main__":  # manual smoke: curl it
    with FakeNebiusServer() as srv:
        print("listening on %s (key: %s)" % (srv.base_url, srv.key))
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass
