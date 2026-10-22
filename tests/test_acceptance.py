"""Tests de aceptación: ejecutan los programas reales como procesos aparte.

El servidor corre en este proceso con tablas DynamoDB falsas (para verificar el
impacto en CorporateData y CorporateLog) y los programas se lanzan con los
mismos comandos que indica el enunciado.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import Env, can_connect, free_port, wait_for

ROOT = Path(__file__).resolve().parent.parent

TUPLE = {
    "id": "UADER-FCyT-IS2",
    "cp": "3260",
    "CUIT": "30-70925411-8",
    "domicilio": "25 de Mayo 385-1P",
    "idreq": "473",
    "idSeq": "1146",
    "localidad": "Concepción del Uruguay",
    "provincia": "Entre Rios",
    "sede": "FCyT",
    "seqID": "23",
    "telefono": "03442 43-1442",
    "web": "http://www.uader.edu.ar",
}


def run(
    script: str, *args: str, timeout: float = 30
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / script), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=ROOT,
        check=False,
    )


def write_json(path: Path, data: Any) -> str:
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def client(env: Env, tmp_path: Path, request: dict[str, Any], name: str) -> Any:
    """Ejecuta singletonclient.py y devuelve (proceso, contenido del output)."""
    out = tmp_path / f"{name}-out.json"
    proc = run(
        "singletonclient.py",
        f"-i={write_json(tmp_path / f'{name}-in.json', request)}",
        f"-o={out}",
        "-s=127.0.0.1",
        f"-p={env.port}",
    )
    return proc, (read_json(out) if out.exists() else None)


@pytest.mark.parametrize(
    ("script", "args"),
    [
        ("singletonclient.py", []),
        ("singletonclient.py", ["-i"]),
        ("singletonclient.py", ["-i=x.json", "-p=abc"]),
        ("singletonclient.py", ["-i=x.json", "-p=99999"]),
        ("singletonclient.py", ["-i=x.json", "--bogus"]),
        ("observerclient.py", ["-p=abc"]),
        ("observerclient.py", ["-p=0"]),
        ("observerclient.py", ["-r=abc"]),
        ("observerclient.py", ["--bogus"]),
        ("singletonproxyobserver.py", ["-p=abc"]),
        ("singletonproxyobserver.py", ["-p=65536"]),
        ("singletonproxyobserver.py", ["--bogus"]),
    ],
)
def test_each_program_rejects_malformed_arguments(script: str, args: list[str]) -> None:
    proc = run(script, *args)
    assert proc.returncode == 2
    assert "usage" in proc.stderr.lower()


def test_happy_path_set_get_list_with_audit_trail(env: Env, tmp_path: Path) -> None:
    request = {"UUID": "cpu-1", "ID": TUPLE["id"], "ACTION": "set", **TUPLE}
    proc, saved = client(env, tmp_path, request, "set")
    assert proc.returncode == 0, proc.stderr
    assert saved == TUPLE
    assert env.data_table.items[TUPLE["id"]] == TUPLE

    proc, got = client(
        env, tmp_path, {"UUID": "cpu-1", "ID": TUPLE["id"], "ACTION": "get"}, "get"
    )
    assert proc.returncode == 0 and got == TUPLE

    proc, listing = client(env, tmp_path, {"UUID": "cpu-1", "ACTION": "list"}, "list")
    assert proc.returncode == 0 and listing == [TUPLE]

    assert env.actions() == ["get", "list", "set"]
    for entry in env.log_table.items.values():
        assert entry["UUID"] == "cpu-1"
        assert entry["sessionid"] and entry["timestamp"] and entry["CPUid"]
    ids = {e["action"]: e.get("item_id") for e in env.log_table.items.values()}
    assert ids["get"] == TUPLE["id"] and ids["list"] is None


def test_set_only_changes_reported_fields_and_blanks_new_records(
    env: Env, tmp_path: Path
) -> None:
    client(env, tmp_path, {"UUID": "u", "ID": "X", "ACTION": "set", "cp": "1"}, "a")
    _, updated = client(
        env, tmp_path, {"UUID": "u", "ID": "X", "ACTION": "set", "sede": "S"}, "b"
    )
    assert updated["cp"] == "1" and updated["sede"] == "S"
    assert updated["web"] == "" and updated["CUIT"] == ""


def test_output_goes_to_stdout_when_no_file_is_given(env: Env, tmp_path: Path) -> None:
    infile = write_json(tmp_path / "in.json", {"UUID": "u", "ACTION": "list"})
    proc = run("singletonclient.py", f"-i={infile}", "-s=127.0.0.1", f"-p={env.port}")
    assert proc.returncode == 0
    assert json.loads(proc.stdout) == []


def test_verbose_flag_enables_debug_on_stdout(env: Env, tmp_path: Path) -> None:
    infile = write_json(tmp_path / "in.json", {"UUID": "u", "ACTION": "list"})
    args = [f"-i={infile}", "-s=127.0.0.1", f"-p={env.port}"]
    assert "DEBUG" in run("singletonclient.py", *args, "-v").stdout
    assert "DEBUG" not in run("singletonclient.py", *args).stdout


@pytest.mark.parametrize(
    "request_",
    [
        {"ACTION": "list"},
        {"UUID": "u"},
        {"UUID": "u", "ACTION": "get"},
        {"UUID": "u", "ACTION": "set"},
        {"UUID": "u", "ACTION": "borrar"},
    ],
)
def test_request_without_minimum_data_is_answered_with_error(
    env: Env, tmp_path: Path, request_: dict[str, Any]
) -> None:
    proc, reply = client(env, tmp_path, request_, "bad")
    assert proc.returncode == 3
    assert reply["STATUS"] == "Error"
    assert env.data_table.items == {} and env.log_table.items == {}


def test_missing_or_broken_input_file_is_reported(tmp_path: Path) -> None:
    missing = run("singletonclient.py", f"-i={tmp_path / 'nada.json'}")
    assert missing.returncode == 2 and "Error" in missing.stderr
    broken = tmp_path / "roto.json"
    broken.write_text("{ no es json", encoding="utf-8")
    assert run("singletonclient.py", f"-i={broken}").returncode == 2


def test_client_reports_a_fallen_server(tmp_path: Path) -> None:
    infile = write_json(tmp_path / "in.json", {"UUID": "u", "ACTION": "list"})
    proc = run("singletonclient.py", f"-i={infile}", f"-p={free_port()}")
    assert proc.returncode == 1
    assert "sin respuesta del servidor" in proc.stderr


def _retries(err_file: Path) -> int:
    """Cuenta los reintentos informados (el texto del SO puede tener tildes)."""
    text = err_file.read_text(encoding="utf-8", errors="replace")
    return text.count("Reintentando")


def test_observer_client_retries_while_the_server_is_down(tmp_path: Path) -> None:
    err_file = tmp_path / "observer-err.txt"
    command = [
        sys.executable,
        str(ROOT / "observerclient.py"),
        "-s=127.0.0.1",
        f"-p={free_port()}",
        "-r=0.2",
    ]
    with err_file.open("w", encoding="utf-8") as err_handle:
        proc = subprocess.Popen(
            command, stdout=subprocess.DEVNULL, stderr=err_handle, cwd=ROOT
        )
        try:
            assert wait_for(lambda: _retries(err_file) >= 2, timeout=30)
            assert proc.poll() is None  # sigue intentando, no termina solo
        finally:
            proc.terminate()
            proc.wait(timeout=10)


def test_observer_client_shows_each_update_on_stdout_and_file(
    env: Env, tmp_path: Path
) -> None:
    out = tmp_path / "observer.json"
    command = [
        sys.executable,
        str(ROOT / "observerclient.py"),
        "-s=127.0.0.1",
        f"-p={env.port}",
        f"-o={out}",
    ]
    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=ROOT,
    )
    try:
        assert wait_for(lambda: len(env.proxy.subscriptions) == 1, timeout=15)
        client(env, tmp_path, {"UUID": "u", "ID": "A", "ACTION": "set", "cp": "1"}, "1")
        client(env, tmp_path, {"UUID": "u", "ID": "B", "ACTION": "set", "cp": "2"}, "2")
        assert wait_for(
            lambda: out.exists() and len(out.read_text().splitlines()) == 2, timeout=15
        )
        assert proc.poll() is None  # mantiene abierto el puerto
    finally:
        proc.terminate()
        stdout, _ = proc.communicate(timeout=10)
    records = [json.loads(line) for line in out.read_text().splitlines()]
    assert [r["id"] for r in records] == ["A", "B"]
    assert [json.loads(line)["id"] for line in stdout.splitlines()] == ["A", "B"]
    assert "subscribe" in env.actions()


def test_server_cannot_be_started_twice() -> None:
    port = free_port()
    command = [sys.executable, str(ROOT / "singletonproxyobserver.py"), f"-p={port}"]
    first = subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        cwd=ROOT,
    )
    try:
        assert wait_for(lambda: can_connect(port), timeout=15)
        second = run("singletonproxyobserver.py", f"-p={port}")
        assert second.returncode == 1
        assert "No se puede escuchar" in second.stderr
        assert first.poll() is None  # el primero sigue sirviendo
    finally:
        first.terminate()
        first.wait(timeout=10)
