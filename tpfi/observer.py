"""Patrón Observer: gestión de suscripciones."""

from __future__ import annotations

import logging
import socket
import threading
from abc import ABC, abstractmethod
from typing import Any

from tpfi.protocol import encode

logger = logging.getLogger("tpfi.observer")


class Observer(ABC):
    """Interfaz de un suscriptor."""

    uuid: str

    @abstractmethod
    def update(self, message: Any) -> bool:
        """Recibe una notificación; devuelve ``False`` si dejó de ser válido."""

    @abstractmethod
    def close(self) -> None:
        """Libera los recursos del suscriptor."""


class SocketObserver(Observer):
    """Suscriptor cuyo canal de notificación es un socket TCP."""

    def __init__(self, uuid: str, sock: socket.socket) -> None:
        """Asocia el UUID del cliente con su socket abierto."""
        self.uuid = uuid
        self.sock = sock
        self._send_lock = threading.Lock()

    def update(self, message: Any) -> bool:
        """Envía la notificación por el socket."""
        try:
            with self._send_lock:
                self.sock.sendall(encode(message))
        except OSError as exc:
            logger.debug("observer %s caído: %s", self.uuid, exc)
            return False
        return True

    def close(self) -> None:
        """Cierra el socket del suscriptor."""
        try:
            self.sock.close()
        except OSError as exc:
            logger.debug("error al cerrar observer %s: %s", self.uuid, exc)


class Subject:
    """Sujeto observable: mantiene y notifica a los suscriptores."""

    def __init__(self) -> None:
        """Crea la lista de suscriptores vacía."""
        self._observers: list[Observer] = []
        self._lock = threading.Lock()

    def attach(self, observer: Observer) -> None:
        """Registra un suscriptor."""
        with self._lock:
            self._observers.append(observer)

    def detach(self, observer: Observer) -> None:
        """Quita un suscriptor si estaba registrado."""
        with self._lock:
            if observer in self._observers:
                self._observers.remove(observer)

    def __len__(self) -> int:
        """Cantidad de suscriptores."""
        with self._lock:
            return len(self._observers)

    def notify(self, message: Any) -> int:
        """Notifica a todos y elimina los caídos; devuelve los entregados."""
        with self._lock:
            observers = list(self._observers)
        delivered = 0
        for observer in observers:
            if observer.update(message):
                delivered += 1
            else:
                self.detach(observer)
                observer.close()
        return delivered

    def close_all(self) -> None:
        """Cierra y elimina a todos los suscriptores."""
        with self._lock:
            observers, self._observers = self._observers, []
        for observer in observers:
            observer.close()


class SubscriptionManager(Subject):
    """Gestor de suscripciones del servidor."""

    def subscribe(self, uuid: str, sock: socket.socket) -> SocketObserver:
        """Registra un socket como suscriptor."""
        observer = SocketObserver(uuid, sock)
        self.attach(observer)
        return observer
