"""Tests de acceso a CorporateData y CorporateLog."""

from __future__ import annotations

from tests.conftest import FakeTable
from tpfi.config import CORPORATE_FIELDS
from tpfi.db.data_table import CorporateDataDB
from tpfi.db.keys import discover_key
from tpfi.db.log_table import CorporateLogDB


class SchemaTable(FakeTable):
    """Tabla falsa que informa su esquema de claves."""

    def __init__(self, key: str, key_type: str = "HASH") -> None:
        super().__init__(key=key)
        self.key_schema = [{"AttributeName": key, "KeyType": key_type}]


class BrokenSchemaTable(FakeTable):
    @property
    def key_schema(self) -> list[dict[str, str]]:
        raise RuntimeError("sin permisos")


def test_get_missing_returns_none() -> None:
    assert CorporateDataDB(FakeTable()).get("nada") is None


def test_set_new_fills_blank_fields() -> None:
    db = CorporateDataDB(FakeTable())
    item = db.set("A", {"cp": "3260"})
    assert item["cp"] == "3260"
    assert item["id"] == "A"
    assert set(item) == set(CORPORATE_FIELDS)
    assert item["web"] == ""


def test_set_existing_keeps_unreported_fields() -> None:
    db = CorporateDataDB(FakeTable())
    db.set("A", {"cp": "3260", "sede": "FCyT"})
    item = db.set("A", {"sede": "Central"})
    assert item["cp"] == "3260"
    assert item["sede"] == "Central"


def test_set_ignores_unknown_fields() -> None:
    db = CorporateDataDB(FakeTable())
    assert "basura" not in db.set("A", {"basura": 1})


def test_set_key_argument_wins_over_tuple_id() -> None:
    db = CorporateDataDB(FakeTable())
    assert db.set("A", {"id": "otro"})["id"] == "A"


def test_list_paginates() -> None:
    db = CorporateDataDB(FakeTable(page_size=2))
    for key in ("A", "B", "C", "D", "E"):
        db.set(key, {})
    assert {i["id"] for i in db.list()} == {"A", "B", "C", "D", "E"}


def test_key_name_is_discovered_from_schema() -> None:
    table = SchemaTable("uid")
    db = CorporateDataDB(table)
    assert db.key_name == "uid"
    db.set("A", {"cp": "1"})
    assert "A" in table.items
    assert db.get("A") is not None


def test_discover_key_falls_back() -> None:
    assert discover_key(FakeTable(), "id") == "id"
    assert discover_key(BrokenSchemaTable(), "pk") == "pk"
    assert discover_key(SchemaTable("uid"), "id") == "uid"


def test_discover_key_without_hash_uses_default() -> None:
    assert discover_key(SchemaTable("orden", "RANGE"), "id") == "id"


def test_log_record_fields() -> None:
    table = FakeTable()
    entry = CorporateLogDB(table).record("123", "sess", "get", "A")
    stored = table.items[entry["id"]]
    assert stored["UUID"] == "123"
    assert stored["sessionid"] == "sess"
    assert stored["action"] == "get"
    assert stored["item_id"] == "A"
    assert "timestamp" in stored
    assert stored["CPUid"].isdigit()
    assert "platform" in stored


def test_log_record_without_item_id() -> None:
    entry = CorporateLogDB(FakeTable()).record("123", "sess", "list")
    assert "item_id" not in entry


def test_log_uses_discovered_key() -> None:
    table = SchemaTable("logid")
    entry = CorporateLogDB(table).record("1", "s", "list")
    assert entry["logid"] in table.items
