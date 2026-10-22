"""Tests del servidor TCP (con tablas falsas y sockets reales en localhost)."""

from __future__ import annotations

import socket
import threading
from typing import Any

import pytest

from tests.conftest import Env, build_env, can_connect, free_port, wait_for
from tpfi.clients import SingletonClient
from tpfi.net import iter_lines, read_message
from tpfi.protocol import ProtocolError, decode_json, encode
from tpfi.server import ProxyServer, ServerStartError


def ask(env: Env, request: dict[str, Any]) -> Any:
    return SingletonClient("127.0.0.1", env.port).request(request)


def raw_exchange(env: Env, payload: bytes) -> Any:
    """Envía bytes crudos y devuelve la respuesta decodificada."""
    with socket.create_connection(("127.0.0.1", env.port), timeout=5) as sock:
        sock.sendall(payload)
        return decode_json(read_message(sock))


def test_set_get_list_return_records_and_audit(env: Env) -> None:
    saved = ask(env, {"UUID": "c1", "ACTION": "set", "ID": "A", "cp": "3260"})
    assert saved["id"] == "A" and saved["cp"] == "3260"
    assert ask(env, {"UUID": "c1", "ACTION": "get", "ID": "A"}) == saved
    assert ask(env, {"UUID": "c1", "ACTION": "list"}) == [saved]
    assert env.actions() == ["get", "list", "set"]
    assert env.data_table.items["A"]["cp"] == "3260"


def test_get_missing_returns_error_record(env: Env) -> None:
    reply = ask(env, {"UUID": "c1", "ACTION": "get", "ID": "nada"})
    assert reply["STATUS"] == "Error"
    assert "inexistente" in reply["ERROR"]


def test_list_of_empty_table_is_empty_array(env: Env) -> None:
    assert ask(env, {"UUID": "c1", "ACTION": "list"}) == []


@pytest.mark.parametrize(
    "request_",
    [
        {"ACTION": "list"},
        {"UUID": "c1"},
        {"UUID": "c1", "ACTION": "borrar"},
        {"UUID": "c1", "ACTION": "get"},
        {"UUID": "c1", "ACTION": "set"},
    ],
)
def test_requests_without_minimum_data_get_error(
    env: Env, request_: dict[str, Any]
) -> None:
    reply = ask(env, request_)
    assert reply["STATUS"] == "Error"
    assert env.log_table.items == {}
    assert env.data_table.items == {}


@pytest.mark.parametrize("payload", [b"esto no es json\n", b"[1, 2, 3]\n", b"\n"])
def test_malformed_payload_gets_error_and_server_survives(
    env: Env, payload: bytes
) -> None:
    assert raw_exchange(env, payload)["STATUS"] == "Error"
    assert ask(env, {"UUID": "c1", "ACTION": "list"}) == []


def test_request_without_trailing_newline_is_accepted(env: Env) -> None:
    with socket.create_connection(("127.0.0.1", env.port), timeout=5) as sock:
        sock.sendall(b'{"UUID": "c1", "ACTION": "list"}')
        sock.shutdown(socket.SHUT_WR)
        assert decode_json(read_message(sock)) == []


def test_client_that_disconnects_without_sending_does_not_hurt(env: Env) -> None:
    socket.create_connection(("127.0.0.1", env.port), timeout=5).close()
    assert ask(env, {"UUID": "c1", "ACTION": "list"}) == []


def test_subscribe_gets_ack_and_then_notifications(env: Env) -> None:
    with socket.create_connection(("127.0.0.1", env.port), timeout=5) as sock:
        sock.settimeout(5)
        sock.sendall(encode({"UUID": "obs", "ACTION": "subscribe"}))
        lines = iter_lines(sock)
        ack = decode_json(next(lines))
        assert ack == {"UUID": "obs", "ACTION": "subscribe", "STATUS": "OK"}
        assert wait_for(lambda: len(env.proxy.subscriptions) == 1)
        saved = ask(env, {"UUID": "c1", "ACTION": "set", "ID": "A", "sede": "FCyT"})
        assert decode_json(next(lines)) == saved
    assert "subscribe" in env.actions()


def test_set_is_retransmitted_to_every_subscriber(env: Env) -> None:
    socks = [socket.create_connection(("127.0.0.1", env.port), timeout=5) for _ in "ab"]
    try:
        readers = []
        for index, sock in enumerate(socks):
            sock.settimeout(5)
            sock.sendall(encode({"UUID": f"obs{index}", "ACTION": "subscribe"}))
            readers.append(iter_lines(sock))
            next(readers[-1])  # acuse
        assert wait_for(lambda: len(env.proxy.subscriptions) == 2)
        saved = ask(env, {"UUID": "c1", "ACTION": "set", "ID": "B", "cp": "1"})
        assert [decode_json(next(r)) for r in readers] == [saved, saved]
    finally:
        for sock in socks:
            sock.close()


def test_dead_subscriber_is_dropped_on_next_change(env: Env) -> None:
    sock = socket.create_connection(("127.0.0.1", env.port), timeout=5)
    sock.sendall(encode({"UUID": "obs", "ACTION": "subscribe"}))
    assert wait_for(lambda: len(env.proxy.subscriptions) == 1)
    sock.close()
    for _ in range(5):  # el primer envío a un socket cerrado puede no fallar
        ask(env, {"UUID": "c1", "ACTION": "set", "ID": "A", "cp": "1"})
        if wait_for(lambda: len(env.proxy.subscriptions) == 0, timeout=0.5):
            break
    assert len(env.proxy.subscriptions) == 0


def test_invalid_subscribe_is_rejected(env: Env) -> None:
    reply = raw_exchange(env, encode({"ACTION": "subscribe"}))
    assert reply["STATUS"] == "Error"
    assert len(env.proxy.subscriptions) == 0


def test_second_server_on_same_port_fails(env: Env) -> None:
    second = ProxyServer(env.proxy, "127.0.0.1", env.port)
    with pytest.raises(ServerStartError):
        second.start()


def test_stop_closes_subscribers_and_frees_the_port() -> None:
    env = build_env()
    port = env.port
    sock = socket.create_connection(("127.0.0.1", port), timeout=5)
    sock.settimeout(5)
    sock.sendall(encode({"UUID": "obs", "ACTION": "subscribe"}))
    next(iter_lines(sock))
    assert wait_for(lambda: len(env.proxy.subscriptions) == 1)
    env.server.stop()
    env.server.stop()  # idempotente
    assert sock.recv(10) == b""  # el servidor cerró la conexión
    sock.close()
    again = build_env(port)  # el puerto quedó libre
    again.server.stop()


def test_serve_forever_blocks_until_event_is_set() -> None:
    env = build_env()
    stop = threading.Event()
    worker = threading.Thread(target=env.server.serve_forever, args=(stop,))
    worker.start()
    assert ask(env, {"UUID": "c1", "ACTION": "list"}) == []
    stop.set()
    worker.join(timeout=5)
    assert not worker.is_alive()


def test_serve_forever_starts_the_server_if_needed() -> None:
    env = build_env()
    env.server.stop()
    server = ProxyServer(env.proxy, "127.0.0.1", free_port())
    stop = threading.Event()
    worker = threading.Thread(target=server.serve_forever, args=(stop,))
    worker.start()
    assert wait_for(lambda: can_connect(server.port))
    stop.set()
    worker.join(timeout=5)


def test_read_message_rejects_oversized_input() -> None:
    left, right = socket.socketpair()
    with left, right:
        left.sendall(b"x" * 100)
        with pytest.raises(ProtocolError):
            read_message(right, max_bytes=10)


def test_iter_lines_splits_and_skips_blank_lines() -> None:
    left, right = socket.socketpair()
    with left, right:
        left.sendall(b'{"a": 1}\n\n{"b"')
        left.sendall(b": 2}\n")
        left.close()
        assert [decode_json(x) for x in iter_lines(right)] == [{"a": 1}, {"b": 2}]


def test_iter_lines_stops_on_event() -> None:
    left, right = socket.socketpair()
    with left, right:
        right.settimeout(0.05)
        stop = threading.Event()
        timer = threading.Timer(0.2, stop.set)
        timer.start()
        assert list(iter_lines(right, stop)) == []
        timer.join()
