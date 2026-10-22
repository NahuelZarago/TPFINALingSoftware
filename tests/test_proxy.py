"""Tests del patrón Proxy (camino feliz, errores, auditoría y patrón)."""

from __future__ import annotations

from typing import Any, cast

from tests.conftest import FakeSocket, FakeTable
from tpfi.db.data_table import CorporateDataDB
from tpfi.db.log_table import CorporateLogDB
from tpfi.observer import SubscriptionManager
from tpfi.protocol import decode
from tpfi.proxy import CorporateDataProxy
from tpfi.service import DataService


def _actions(log_table: FakeTable) -> list[str]:
    return sorted(e["action"] for e in log_table.items.values())


def test_set_then_get(proxy: CorporateDataProxy, log_table: FakeTable) -> None:
    reply = proxy.handle({"UUID": "1", "ACTION": "set", "ID": "A", "cp": "3260"})
    assert reply["STATUS"] == "OK"
    assert reply["DATA"]["cp"] == "3260"
    reply = proxy.handle({"UUID": "1", "ACTION": "get", "ID": "A"})
    assert reply["STATUS"] == "OK"
    assert reply["DATA"]["id"] == "A"
    assert _actions(log_table) == ["get", "set"]


def test_get_missing_is_error_but_audited(
    proxy: CorporateDataProxy, log_table: FakeTable
) -> None:
    reply = proxy.handle({"UUID": "1", "ACTION": "get", "ID": "no"})
    assert reply["STATUS"] == "Error"
    assert _actions(log_table) == ["get"]


def test_list(proxy: CorporateDataProxy, log_table: FakeTable) -> None:
    proxy.handle({"UUID": "1", "ACTION": "set", "ID": "A"})
    proxy.handle({"UUID": "1", "ACTION": "set", "ID": "B"})
    reply = proxy.handle({"UUID": "1", "ACTION": "list"})
    assert {i["id"] for i in reply["DATA"]} == {"A", "B"}
    assert "list" in _actions(log_table)


def test_audit_records_uuid_session_and_item(
    proxy: CorporateDataProxy, log_table: FakeTable
) -> None:
    proxy.handle({"UUID": "cpu-1", "ACTION": "get", "ID": "A", "SESSION": "s-9"})
    (entry,) = log_table.items.values()
    assert entry["UUID"] == "cpu-1"
    assert entry["sessionid"] == "s-9"
    assert entry["item_id"] == "A"
    assert entry["action"] == "get"
    assert entry["timestamp"]


def test_session_is_generated_when_missing(
    proxy: CorporateDataProxy, log_table: FakeTable
) -> None:
    proxy.handle({"UUID": "1", "ACTION": "list"})
    (entry,) = log_table.items.values()
    assert len(entry["sessionid"]) == 36  # uuid4


def test_invalid_request_is_not_audited(
    proxy: CorporateDataProxy, log_table: FakeTable
) -> None:
    reply = proxy.handle({"ACTION": "get"})
    assert reply["STATUS"] == "Error"
    assert log_table.items == {}


def test_subscribe_is_audited_without_touching_data(
    proxy: CorporateDataProxy, data_table: FakeTable, log_table: FakeTable
) -> None:
    reply = proxy.handle({"UUID": "obs", "ACTION": "subscribe"})
    assert reply["STATUS"] == "OK"
    assert _actions(log_table) == ["subscribe"]
    assert data_table.items == {}


def test_set_notifies_subscribers_with_the_record(
    proxy: CorporateDataProxy,
) -> None:
    sock = FakeSocket()
    proxy.subscriptions.subscribe("obs", cast(Any, sock))
    proxy.handle({"UUID": "1", "ACTION": "set", "ID": "A", "sede": "FCyT"})
    note = decode(sock.sent[0])
    assert note["id"] == "A"
    assert note["sede"] == "FCyT"


def test_get_does_not_notify(proxy: CorporateDataProxy) -> None:
    sock = FakeSocket()
    proxy.subscriptions.subscribe("obs", cast(Any, sock))
    proxy.handle({"UUID": "1", "ACTION": "set", "ID": "A"})
    proxy.handle({"UUID": "1", "ACTION": "get", "ID": "A"})
    proxy.handle({"UUID": "1", "ACTION": "list"})
    assert len(sock.sent) == 1


def test_set_ignores_control_keys_as_fields(
    proxy: CorporateDataProxy, data_table: FakeTable
) -> None:
    proxy.handle({"UUID": "1", "ACTION": "set", "ID": "A", "SESSION": "x", "cp": "1"})
    stored = data_table.items["A"]
    assert "UUID" not in stored and "ACTION" not in stored and "SESSION" not in stored


def test_backend_failure_returns_error() -> None:
    class Broken(FakeTable):
        def get_item(self, Key: dict[str, Any]) -> dict[str, Any]:  # noqa: N803
            raise RuntimeError("DynamoDB caído")

    proxy = CorporateDataProxy(
        CorporateDataDB(Broken()),
        CorporateLogDB(FakeTable()),
        SubscriptionManager(),
    )
    reply = proxy.handle({"UUID": "1", "ACTION": "get", "ID": "A"})
    assert reply["STATUS"] == "Error"
    assert "caído" in reply["DATA"]


def test_audit_failure_blocks_the_access() -> None:
    class NoLog(FakeTable):
        def put_item(self, Item: dict[str, Any]) -> None:  # noqa: N803
            raise RuntimeError("log caído")

    data = FakeTable()
    proxy = CorporateDataProxy(
        CorporateDataDB(data), CorporateLogDB(NoLog()), SubscriptionManager()
    )
    reply = proxy.handle({"UUID": "1", "ACTION": "set", "ID": "A"})
    assert reply["STATUS"] == "Error"
    assert data.items == {}  # sin auditoría no se modifica nada


def test_proxy_and_real_subject_share_the_interface(
    proxy: CorporateDataProxy,
) -> None:
    assert isinstance(proxy, DataService)
    assert isinstance(CorporateDataDB(FakeTable()), DataService)


class SpySubject:
    """Sujeto real falso que anota el orden de las llamadas."""

    def __init__(self, events: list[str]) -> None:
        self.events = events

    def get(self, key: str) -> dict[str, Any] | None:
        self.events.append(f"subject.get:{key}")
        return {"id": key}

    def set(self, key: str, fields: dict[str, Any]) -> dict[str, Any]:
        self.events.append(f"subject.set:{key}")
        return {"id": key, **fields}

    def list(self) -> list[dict[str, Any]]:
        self.events.append("subject.list")
        return []


def test_proxy_audits_before_delegating_to_the_subject() -> None:
    events: list[str] = []

    class SpyLog(FakeTable):
        def put_item(self, Item: dict[str, Any]) -> None:  # noqa: N803
            events.append(f"audit:{Item['action']}")
            super().put_item(Item)

    proxy = CorporateDataProxy(
        SpySubject(events), CorporateLogDB(SpyLog()), SubscriptionManager()
    )
    proxy.get("A", client="c", session="s")
    proxy.set("A", {"cp": "1"}, client="c", session="s")
    proxy.list(client="c", session="s")
    assert events == [
        "audit:get",
        "subject.get:A",
        "audit:set",
        "subject.set:A",
        "audit:list",
        "subject.list",
    ]
