"""Tests del patrón Singleton."""

from __future__ import annotations

import threading
from typing import Any

from tests.conftest import FakeTable
from tpfi.db.data_table import CorporateDataDB
from tpfi.db.log_table import CorporateLogDB
from tpfi.singleton import SingletonMeta


def test_same_instance_returned() -> None:
    a = CorporateDataDB(FakeTable())
    b = CorporateDataDB()
    assert a is b


def test_constructor_arguments_are_ignored_after_first_instance() -> None:
    first_table = FakeTable()
    db = CorporateDataDB(first_table)
    assert CorporateDataDB(FakeTable()).table is first_table
    assert db.table is first_table


def test_data_and_log_are_independent_singletons() -> None:
    data = CorporateDataDB(FakeTable())
    log = CorporateLogDB(FakeTable())
    assert data is not log
    assert CorporateLogDB() is log


def test_classes_use_the_singleton_metaclass() -> None:
    assert isinstance(CorporateDataDB, SingletonMeta)
    assert isinstance(CorporateLogDB, SingletonMeta)


def test_reset_single_class() -> None:
    first = CorporateDataDB(FakeTable())
    SingletonMeta.reset(CorporateDataDB)
    assert CorporateDataDB(FakeTable()) is not first


def test_reset_all() -> None:
    first = CorporateLogDB(FakeTable())
    SingletonMeta.reset()
    assert CorporateLogDB(FakeTable()) is not first


def test_thread_safe_creation() -> None:
    found: list[Any] = []

    def create() -> None:
        found.append(CorporateDataDB(FakeTable()))

    threads = [threading.Thread(target=create) for _ in range(16)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len({id(instance) for instance in found}) == 1
