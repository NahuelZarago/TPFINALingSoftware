"""Tests de SingletonClient y ObserverClient."""

from __future__ import annotations

import json
import socket
import threading
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import FakeTable, build_env, free_port, wait_for
from tpfi.clients import ObserverClient, SingletonClient
from tpfi.db.data_table import CorporateDataDB
from tpfi.db.log_table import CorporateLogDB
from tpfi.observer import SubscriptionManager
from tpfi.protocol import encode
from tpfi.proxy import CorporateDataProxy
from tpfi.server import ProxyServer


def run_in_thread(client: ObserverClient) -> tuple[threading.Thread, threading.Event]:
    stop = threading.Event()
    thread = threading.Thread(target=client.run, args=(stop,), daemon=True)
    thread.start()
    return thread, stop


def lines(path: Path) -> list[Any]:
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]


def test_singleton_client_server_down_raises_oserror() -> None:
    client = SingletonClient("127.0.0.1", free_port(), timeout=1)
    with pytest.raises(OSError):
        client.request({"UUID": "1", "ACTION": "list"})


def test_singleton_client_empty_reply_is_an_error() -> None:
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen()

    def accept_and_close() -> None:
        conn, _ = server.accept()
        conn.close()

    threading.Thread(target=accept_and_close, daemon=True).start()
    client = SingletonClient("127.0.0.1", server.getsockname()[1], timeout=2)
    with pytest.raises(ConnectionError):
        client.request({"UUID": "1", "ACTION": "list"})
    server.close()


def test_observer_receives_every_change(tmp_path: Path) -> None:
    env = build_env()
    out = tmp_path / "out.json"
    observer = ObserverClient("127.0.0.1", env.port, out, retry_seconds=0.1)
    thread, stop = run_in_thread(observer)
    try:
        assert wait_for(lambda: len(env.proxy.subscriptions) == 1)
        client = SingletonClient("127.0.0.1", env.port)
        client.request({"UUID": "c", "ACTION": "set", "ID": "A", "cp": "1"})
        client.request({"UUID": "c", "ACTION": "set", "ID": "B", "cp": "2"})
        assert wait_for(lambda: len(lines(out)) == 2)
        assert [r["id"] for r in lines(out)] == ["A", "B"]
        assert observer.received == 2
    finally:
        stop.set()
        thread.join(timeout=5)
        env.server.stop()
    assert not thread.is_alive()


def test_observer_reconnects_and_resubscribes_after_server_restart(
    tmp_path: Path,
) -> None:
    first = build_env()
    port = first.port
    out = tmp_path / "out.json"
    observer = ObserverClient("127.0.0.1", port, out, retry_seconds=0.1)
    thread, stop = run_in_thread(observer)
    try:
        assert wait_for(lambda: len(first.proxy.subscriptions) == 1)
        first.server.stop()
        second = build_env(port)
        assert wait_for(lambda: len(second.proxy.subscriptions) == 1, timeout=10)
        SingletonClient("127.0.0.1", port).request(
            {"UUID": "c", "ACTION": "set", "ID": "Z", "cp": "9"}
        )
        assert wait_for(lambda: len(lines(out)) == 1)
        assert lines(out)[0]["id"] == "Z"
        second.server.stop()
    finally:
        stop.set()
        thread.join(timeout=5)


def test_observer_waits_for_a_server_that_is_not_up_yet(tmp_path: Path) -> None:
    port = free_port()
    out = tmp_path / "out.json"
    observer = ObserverClient("127.0.0.1", port, out, retry_seconds=0.1)
    thread, stop = run_in_thread(observer)
    try:
        assert not wait_for(lambda: observer.received > 0, timeout=0.5)
        env = build_env(port)
        assert wait_for(lambda: len(env.proxy.subscriptions) == 1, timeout=10)
        env.server.stop()
    finally:
        stop.set()
        thread.join(timeout=5)
    assert not thread.is_alive()


def test_observer_gives_up_when_subscription_is_rejected() -> None:
    class NoLog(FakeTable):
        def put_item(self, Item: dict[str, Any]) -> None:  # noqa: N803
            raise RuntimeError("log caído")

    proxy = CorporateDataProxy(
        CorporateDataDB(FakeTable()), CorporateLogDB(NoLog()), SubscriptionManager()
    )
    server = ProxyServer(proxy, "127.0.0.1", 0)
    server.start()
    try:
        observer = ObserverClient("127.0.0.1", server.port, retry_seconds=0.1)
        assert observer.run(threading.Event()) == 3
    finally:
        server.stop()


def test_observer_ignores_garbage_lines_from_server(tmp_path: Path) -> None:
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()

    def serve() -> None:
        conn, _ = listener.accept()
        conn.recv(1024)
        conn.sendall(encode({"UUID": "x", "ACTION": "subscribe", "STATUS": "OK"}))
        conn.sendall(b"basura que no es json\n")
        conn.sendall(encode({"id": "ok"}))
        threading.Event().wait(0.5)
        conn.close()

    threading.Thread(target=serve, daemon=True).start()
    out = tmp_path / "out.json"
    observer = ObserverClient(
        "127.0.0.1", listener.getsockname()[1], out, retry_seconds=30
    )
    thread, stop = run_in_thread(observer)
    try:
        assert wait_for(lambda: len(lines(out)) == 1)
        assert lines(out) == [{"id": "ok"}]
    finally:
        stop.set()
        thread.join(timeout=5)
        listener.close()


def test_observer_output_error_does_not_stop_it(tmp_path: Path) -> None:
    observer = ObserverClient(output=tmp_path / "no" / "existe" / "out.json")
    observer._emit({"id": "A"})  # no debe lanzar
    assert observer.output is not None
