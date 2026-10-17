"""Startup guard: one backend per port.

Python's development server sets SO_REUSEADDR, which on Windows lets a second
server listen on a port that is already taken. So a second `python run.py`
would not fail: both copies would answer requests (each signing sessions with
its own random key, so sign-ins break at random) and both would run the
background jobs. run.py and serve.py call this before create_app() starts them.
"""
import json
import socket
import sys
from urllib.request import urlopen

WILDCARD_HOSTS = ("", "0.0.0.0", "::")


def port_in_use(host, port):
    """True if something already accepts connections on host:port."""
    try:
        socket.create_connection((_probe_host(host), port), timeout=1).close()
        return True
    except OSError:
        return False


def exit_if_port_in_use(host, port):
    """Exit with a clear message instead of starting a second server on a taken port."""
    if not port_in_use(host, port):
        return
    if _is_planit_backend(host, port):
        sys.exit(f"The PlanIT backend is already running on port {port} (probably in another terminal). "
                 "Use that one, or stop it there with Ctrl+C before starting it again.")
    sys.exit(f"Port {port} is in use by another program. Stop that program, or set PORT to a free port.")


def _probe_host(host):
    # A server bound to every interface is reachable on this machine at 127.0.0.1.
    return "127.0.0.1" if host in WILDCARD_HOSTS else host


def _is_planit_backend(host, port):
    try:
        with urlopen(f"http://{_probe_host(host)}:{port}/api/meta", timeout=2) as response:
            return json.load(response).get("api") == "planit-control"
    except (OSError, ValueError):  # not HTTP, not JSON, or no answer
        return False
