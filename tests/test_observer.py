"""Tests del patrón Observer."""

from __future__ import annotations

from typing import Any, cast

import pytest

from tests.conftest import FakeSocket
from tpfi.observer import Observer, SocketObserver, Subject, SubscriptionManager
from tpfi.protocol import decode


def _sock(broken: bool = False) -> Any:
    return cast(Any, FakeSocket(broken))


class Recorder(Observer):
    """Observer de prueba que acumula lo recibido."""

    def __init__(self) -> None:
        self.uuid = "recorder"
        self.messages: list[Any] = []
        self.closed = False

    def update(self, message: Any) -> bool:
        self.messages.append(message)
        return True

    def close(self) -> None:
        self.closed = True


def test_observer_is_abstract() -> None:
    with pytest.raises(TypeError):
        Observer()  # type: ignore[abstract]


def test_manager_is_a_subject_and_socket_observer_an_observer() -> None:
    assert issubclass(SubscriptionManager, Subject)
    assert issubclass(SocketObserver, Observer)


def test_any_observer_implementation_gets_notified() -> None:
    subject = Subject()
    recorder = Recorder()
    subject.attach(recorder)
    assert subject.notify({"x": 1}) == 1
    assert recorder.messages == [{"x": 1}]


def test_notify_delivers_to_all() -> None:
    manager = SubscriptionManager()
    s1, s2 = _sock(), _sock()
    manager.subscribe("1", s1)
    manager.subscribe("2", s2)
    assert manager.notify({"ACTION": "change"}) == 2
    assert decode(s1.sent[0]) == {"ACTION": "change"}
    assert len(s2.sent) == 1


def test_broken_observer_is_removed_and_closed() -> None:
    manager = SubscriptionManager()
    manager.subscribe("ok", _sock())
    bad = _sock(broken=True)
    manager.subscribe("bad", bad)
    assert len(manager) == 2
    assert manager.notify({"x": 1}) == 1
    assert len(manager) == 1
    assert bad.closed


def test_detach() -> None:
    manager = SubscriptionManager()
    observer = manager.subscribe("1", _sock())
    manager.detach(observer)
    manager.detach(observer)  # idempotente
    assert len(manager) == 0
    assert manager.notify({"x": 1}) == 0


def test_close_all() -> None:
    manager = SubscriptionManager()
    s1, s2 = _sock(), _sock()
    manager.subscribe("1", s1)
    manager.subscribe("2", s2)
    manager.close_all()
    assert len(manager) == 0
    assert s1.closed and s2.closed


def test_socket_observer_close_ignores_errors() -> None:
    class Exploding:
        def close(self) -> None:
            raise OSError("ya cerrado")

    observer = SocketObserver("1", cast(Any, Exploding()))
    observer.close()
