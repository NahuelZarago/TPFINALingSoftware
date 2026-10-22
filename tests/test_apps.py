"""Tests en proceso de los tres programas (argumentos, códigos de salida)."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import Env, FakeTable, can_connect, free_port, wait_for
from tpfi.apps import observerclient, singletonclient, singletonproxyobserver
from tpfi.config import EXIT_BAD_INPUT, EXIT_OK, EXIT_SERVER_ERROR, EXIT_UNREACHABLE
from tpfi.db.data_table import CorporateDataDB
from tpfi.db.log_table import CorporateLogDB
from tpfi.observer import SubscriptionManager
from tpfi.proxy import CorporateDataProxy
from tpfi.server import ProxyServer


def write_json(path: Path, data: Any) -> str:
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


@pytest.mark.parametrize(
    "argv",
    [
        [],
        ["-i"],
        ["-i=x.json", "-p=abc"],
        ["-i=x.json", "-p=0"],
        ["-i=x.json", "-p=99999"],
        ["-i=x.json", "--bogus"],
        ["suelto"],
    ],
)
def test_singletonclient_rejects_malformed_arguments(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        singletonclient.main(argv)
    assert excinfo.value.code == 2


@pytest.mark.parametrize(
    "argv",
    [["-p=abc"], ["-p=0"], ["-r=0"], ["-r=abc"], ["-r=-3"], ["--bogus"], ["suelto"]],
)
def test_observerclient_rejects_malformed_arguments(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        observerclient.main(argv)
    assert excinfo.value.code == 2


@pytest.mark.parametrize(
    "argv", [["-p=abc"], ["-p=0"], ["-p=65536"], ["--bogus"], ["suelto"]]
)
def test_server_rejects_malformed_arguments(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        singletonproxyobserver.main(argv)
    assert excinfo.value.code == 2


def test_option_values_accept_the_equals_form() -> None:
    args = singletonclient.build_parser().parse_args(
        ["-i=in.json", "-o=out.json", "-s=otro", "-p=9090", "-v"]
    )
    assert (args.input, args.output, args.server) == ("in.json", "out.json", "otro")
    assert args.port == 9090 and args.verbose
    args = observerclient.build_parser().parse_args(["-s=h", "-p=1234", "-o=o.json"])
    assert (args.server, args.port, args.output) == ("h", 1234, "o.json")
    assert args.retry == 30.0 and not args.verbose
    assert singletonproxyobserver.build_parser().parse_args([]).port == 8080


def test_singletonclient_happy_path_writes_file(env: Env, tmp_path: Path) -> None:
    out = tmp_path / "out.json"
    request = {"UUID": "u", "ID": "A", "ACTION": "set", "cp": "3260"}
    argv = [f"-i={write_json(tmp_path / 'in.json', request)}", f"-o={out}"]
    argv += ["-s=127.0.0.1", f"-p={env.port}"]
    assert singletonclient.main(argv) == EXIT_OK
    assert json.loads(out.read_text(encoding="utf-8"))["cp"] == "3260"


def test_singletonclient_prints_to_stdout_without_output_option(
    env: Env, tmp_path: Path, capsys: Any
) -> None:
    request = {"UUID": "u", "ACTION": "list"}
    argv = [f"-i={write_json(tmp_path / 'in.json', request)}", f"-p={env.port}"]
    assert singletonclient.main(argv + ["-s=127.0.0.1"]) == EXIT_OK
    assert json.loads(capsys.readouterr().out) == []


def test_singletonclient_server_error_gives_exit_3(env: Env, tmp_path: Path) -> None:
    out = tmp_path / "out.json"
    request = {"UUID": "u", "ID": "no-existe", "ACTION": "get"}
    argv = [f"-i={write_json(tmp_path / 'in.json', request)}", f"-o={out}"]
    code = singletonclient.main(argv + [f"-p={env.port}", "-s=127.0.0.1"])
    assert code == EXIT_SERVER_ERROR
    assert json.loads(out.read_text(encoding="utf-8"))["STATUS"] == "Error"


def test_singletonclient_server_down_gives_exit_1(tmp_path: Path, capsys: Any) -> None:
    request = {"UUID": "u", "ACTION": "list"}
    argv = [f"-i={write_json(tmp_path / 'in.json', request)}", f"-p={free_port()}"]
    assert singletonclient.main(argv + ["-s=127.0.0.1"]) == EXIT_UNREACHABLE
    assert "sin respuesta" in capsys.readouterr().err


def test_singletonclient_bad_input_files_give_exit_2(tmp_path: Path) -> None:
    broken = tmp_path / "roto.json"
    broken.write_text("{no es json", encoding="utf-8")
    not_object = write_json(tmp_path / "lista.json", [1])
    assert singletonclient.main([f"-i={tmp_path / 'falta.json'}"]) == EXIT_BAD_INPUT
    assert singletonclient.main([f"-i={broken}"]) == EXIT_BAD_INPUT
    assert singletonclient.main([f"-i={not_object}"]) == EXIT_BAD_INPUT


def test_singletonclient_unwritable_output_exit_2(env: Env, tmp_path: Path) -> None:
    request = {"UUID": "u", "ACTION": "list"}
    argv = [f"-i={write_json(tmp_path / 'in.json', request)}", f"-p={env.port}"]
    argv += ["-s=127.0.0.1", f"-o={tmp_path / 'no' / 'existe.json'}"]
    assert singletonclient.main(argv) == EXIT_BAD_INPUT


def test_singletonclient_verbose_enables_debug_output(
    env: Env, tmp_path: Path, capsys: Any
) -> None:
    request = {"UUID": "u", "ACTION": "list"}
    argv = [f"-i={write_json(tmp_path / 'in.json', request)}", f"-p={env.port}"]
    singletonclient.main(argv + ["-s=127.0.0.1", "-v"])
    assert "DEBUG" in capsys.readouterr().out
    singletonclient.main(argv + ["-s=127.0.0.1"])
    assert "DEBUG" not in capsys.readouterr().out


def test_observerclient_main_stops_with_the_event() -> None:
    stop = threading.Event()
    stop.set()
    assert observerclient.main(["-p=9", "-s=127.0.0.1"], stop=stop) == EXIT_OK


def test_observerclient_main_handles_keyboard_interrupt(monkeypatch: Any) -> None:
    def interrupt(self: Any, stop: Any = None) -> int:
        raise KeyboardInterrupt

    monkeypatch.setattr(observerclient.ObserverClient, "run", interrupt)
    assert observerclient.main([]) == EXIT_OK


def test_server_main_serves_until_stopped(capsys: Any) -> None:
    proxy = CorporateDataProxy(_real_subject(), _real_log(), SubscriptionManager())
    port = free_port()
    stop = threading.Event()
    result: list[int] = []

    def serve() -> None:
        result.append(singletonproxyobserver.main([f"-p={port}"], proxy, stop))

    worker = threading.Thread(target=serve)
    worker.start()
    try:
        assert wait_for(lambda: can_connect(port))
    finally:
        stop.set()
        worker.join(timeout=5)
    assert result == [EXIT_OK]
    assert f"*:{port}" in capsys.readouterr().out


def test_server_main_refuses_to_start_twice(capsys: Any) -> None:
    proxy = CorporateDataProxy(_real_subject(), _real_log(), SubscriptionManager())
    first = ProxyServer(proxy, "", free_port())
    first.start()
    try:
        code = singletonproxyobserver.main([f"-p={first.port}"], proxy)
        assert code == EXIT_UNREACHABLE
    finally:
        first.stop()
    assert "No se puede escuchar" in capsys.readouterr().err


def test_server_main_handles_keyboard_interrupt(monkeypatch: Any) -> None:
    def interrupt(self: Any, stop: Any = None) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(ProxyServer, "serve_forever", interrupt)
    proxy = CorporateDataProxy(_real_subject(), _real_log(), SubscriptionManager())
    assert singletonproxyobserver.main([f"-p={free_port()}"], proxy) == EXIT_OK


def test_build_proxy_wires_the_singletons_without_touching_aws() -> None:
    proxy = singletonproxyobserver.build_proxy()
    assert isinstance(proxy, CorporateDataProxy)
    assert len(proxy.subscriptions) == 0
    assert CorporateDataDB() is CorporateDataDB()
    assert CorporateLogDB() is CorporateLogDB()


def _real_subject() -> Any:
    return CorporateDataDB(FakeTable())


def _real_log() -> Any:
    return CorporateLogDB(FakeTable())
