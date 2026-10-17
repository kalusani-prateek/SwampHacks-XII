"""Startup guard: a second backend on the same port exits instead of running alongside the first."""
import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from app.ports import exit_if_port_in_use, port_in_use


@contextmanager
def http_server(meta_body):
    """A throwaway HTTP server on a free port; GET /api/meta returns meta_body (404 if None)."""
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/api/meta" and meta_body is not None:
                body = json.dumps(meta_body).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
            else:
                body = b"not found"
                self.send_response(404)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):  # keep test output quiet
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()


def test_port_in_use_sees_a_listening_server():
    with http_server(None) as port:
        assert port_in_use("127.0.0.1", port)
        assert port_in_use("0.0.0.0", port)  # wildcard bind: checks this machine
    assert not port_in_use("127.0.0.1", port)


def test_second_backend_exits_and_says_one_is_already_running():
    with http_server({"api": "planit-control"}) as port:
        with pytest.raises(SystemExit) as exc:
            exit_if_port_in_use("127.0.0.1", port)
    assert "already running" in str(exc.value)


def test_port_taken_by_another_program():
    with http_server(None) as port:
        with pytest.raises(SystemExit) as exc:
            exit_if_port_in_use("127.0.0.1", port)
    assert "another program" in str(exc.value)


def test_free_port_starts_normally():
    with http_server(None) as port:
        pass  # closed again: the port is free
    exit_if_port_in_use("127.0.0.1", port)  # returns without exiting
