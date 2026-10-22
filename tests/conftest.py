"""Fixtures compartidas: tablas DynamoDB falsas, servidor en memoria y utilidades."""

from __future__ import annotations

import socket
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any

import pytest

from tpfi.db.data_table import CorporateDataDB
from tpfi.db.log_table import CorporateLogDB
from tpfi.observer import SubscriptionManager
from tpfi.proxy import CorporateDataProxy
from tpfi.server import ProxyServer
from tpfi.singleton import SingletonMeta


class FakeTable:
    """Tabla DynamoDB en memoria con paginación opcional en scan."""

    def __init__(self, key: str = "id", page_size: int = 0) -> None:
        self.key = key
        self.items: dict[str, dict[str, Any]] = {}
        self.page_size = page_size

    def get_item(self, Key: dict[str, Any]) -> dict[str, Any]:  # noqa: N803
        item = self.items.get(Key[self.key])
        return {"Item": item} if item else {}

    def put_item(self, Item: dict[str, Any]) -> None:  # noqa: N803
        self.items[Item[self.key]] = dict(Item)

    def scan(self, **kwargs: Any) -> dict[str, Any]:
        keys = list(self.items)
        start = 0
        if "ExclusiveStartKey" in kwargs:
            start = keys.index(kwargs["ExclusiveStartKey"][self.key]) + 1
        if not self.page_size:
            return {"Items": [self.items[k] for k in keys[start:]]}
        chunk = keys[start : start + self.page_size]
        result: dict[str, Any] = {"Items": [self.items[k] for k in chunk]}
        if start + self.page_size < len(keys):
            result["LastEvaluatedKey"] = {self.key: chunk[-1]}
        return result


class FakeSocket:
    """Socket falso que acumula lo enviado o falla si está caído."""

    def __init__(self, broken: bool = False) -> None:
        self.sent: list[bytes] = []
        self.broken = broken
        self.closed = False

    def sendall(self, data: bytes) -> None:
        if self.broken:
            raise OSError("socket caído")
        self.sent.append(data)

    def close(self) -> None:
        self.closed = True


@dataclass
class Env:
    """Servidor real en memoria (tablas falsas) escuchando en un puerto libre."""

    server: ProxyServer
    proxy: CorporateDataProxy
    data_table: FakeTable
    log_table: FakeTable

    @property
    def port(self) -> int:
        return self.server.port

    def actions(self) -> list[str]:
        """Acciones registradas en la pista de auditoría, ordenadas."""
        return sorted(e["action"] for e in self.log_table.items.values())


def free_port() -> int:
    """Devuelve un puerto TCP libre en localhost."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def can_connect(port: int) -> bool:
    """Indica si hay algo escuchando en localhost:port."""
    try:
        socket.create_connection(("127.0.0.1", port), timeout=1).close()
    except OSError:
        return False
    return True


def wait_for(predicate: Callable[[], bool], timeout: float = 5.0) -> bool:
    """Espera (con polling) a que se cumpla la condición."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return predicate()


def build_env(port: int = 0) -> Env:
    """Arma proxy y servidor sobre tablas falsas y abre el puerto."""
    data_table, log_table = FakeTable(), FakeTable()
    proxy = CorporateDataProxy(
        CorporateDataDB(data_table), CorporateLogDB(log_table), SubscriptionManager()
    )
    server = ProxyServer(proxy, "127.0.0.1", port)
    server.start()
    return Env(server, proxy, data_table, log_table)


@pytest.fixture(autouse=True)
def _reset_singletons() -> Iterator[None]:
    SingletonMeta.reset()
    yield
    SingletonMeta.reset()


@pytest.fixture
def data_table() -> FakeTable:
    return FakeTable()


@pytest.fixture
def log_table() -> FakeTable:
    return FakeTable()


@pytest.fixture
def proxy(data_table: FakeTable, log_table: FakeTable) -> CorporateDataProxy:
    return CorporateDataProxy(
        CorporateDataDB(data_table),
        CorporateLogDB(log_table),
        SubscriptionManager(),
    )


@pytest.fixture
def env() -> Iterator[Env]:
    environment = build_env()
    yield environment
    environment.server.stop()
