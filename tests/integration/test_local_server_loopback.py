"""The real local-server path, end to end, against an OpenAI-compatible server on loopback.

This exercises ModelFactory, the OpenAI client, HTTP, loopback restriction and the structured-output
fallback. It does not prove a real model's quality; the live tests do that.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from six_hats.config.settings import LLMSettings, LocalServerSettings
from six_hats.hats.base import run_hat
from six_hats.llm.factory import create_model
from tests.support.hats_fake import default_framing

pytestmark = pytest.mark.enable_socket  # loopback only; the server and client both need sockets

HAT_JSON = json.dumps({"hat": "white", "key_points": ["fact one", "fact two", "fact three"]})


def _make_handler(*, reject_response_format: bool, requests: list[dict]):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append(body)
            if reject_response_format and ("response_format" in body or "tools" in body):
                self._send(400, {"error": {"message": "response_format not supported"}})
                return
            self._send(
                200,
                {
                    "id": "chatcmpl-1",
                    "object": "chat.completion",
                    "created": 0,
                    "model": body.get("model", "m"),
                    "choices": [
                        {
                            "index": 0,
                            "finish_reason": "stop",
                            "message": {"role": "assistant", "content": HAT_JSON},
                        }
                    ],
                    "usage": {"prompt_tokens": 5, "completion_tokens": 7, "total_tokens": 12},
                },
            )

        def _send(self, status: int, payload: dict) -> None:
            data = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *_args: object) -> None:
            pass

    return Handler


@pytest.fixture
def server(monkeypatch):
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")
    monkeypatch.setenv("no_proxy", "127.0.0.1,localhost")
    started: list[HTTPServer] = []

    def start(*, reject_response_format: bool):
        requests: list[dict] = []
        httpd = HTTPServer(
            ("127.0.0.1", 0),
            _make_handler(reject_response_format=reject_response_format, requests=requests),
        )
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        started.append(httpd)
        return f"http://127.0.0.1:{httpd.server_port}/v1", requests

    yield start
    for httpd in started:
        httpd.shutdown()
        httpd.server_close()


def _model(url: str):
    cfg = LLMSettings(
        provider="local", model="local-model", local=LocalServerSettings(base_url=url)
    )
    return create_model(cfg)


async def test_hat_runs_against_server_with_native_schema_support(server):
    url, requests = server(reject_response_format=False)
    out = await run_hat("white", _model(url), "Is water wet?", default_framing())
    assert out.hat == "white" and out.key_points[0] == "fact one"
    assert requests and "response_format" in requests[0]  # native path was used first


async def test_hat_runs_against_server_without_schema_support(server):
    url, requests = server(reject_response_format=True)
    out = await run_hat("white", _model(url), "Is water wet?", default_framing())
    assert out.hat == "white" and len(out.key_points) == 3
    assert "response_format" in requests[0]  # tried native, got HTTP 400
    assert (
        "response_format" not in requests[-1] and "tools" not in requests[-1]
    )  # JSON-mode fallback
    assert "JSON Schema" in json.dumps(requests[-1]["messages"])


async def test_full_workflow_against_local_server(server):
    from six_hats.graph.runner import run_workflow

    url, _ = server(reject_response_format=True)
    model = _model(url)

    # The canned server always returns a HatOutput, which is valid for hats only. Blue-Open and
    # Blue-Close need their own shapes, so route those nodes to a fake and the hats to the server.
    from tests.support.hats_fake import make_hats_fake

    fake = make_hats_fake()
    report = await run_workflow(
        "Should we do X?", lambda node: model if node in {"white"} else fake, run_id="loop"
    )
    assert report.run_id == "loop"
