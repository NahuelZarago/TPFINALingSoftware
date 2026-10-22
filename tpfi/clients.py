"""Clientes TCP: consulta puntual (SingletonClient) y suscripción (ObserverClient)."""

from __future__ import annotations

import json
import logging
import socket
import sys
import threading
import uuid
from pathlib import Path
from typing import Any

from tpfi.config import DEFAULT_HOST, DEFAULT_PORT, RETRY_SECONDS, SOCKET_TIMEOUT
from tpfi.net import iter_lines, read_message
from tpfi.protocol import ProtocolError, decode_json, encode

logger = logging.getLogger("tpfi.client")


class SubscriptionRejected(RuntimeError):
    """El servidor rechazó la suscripción (reintentar no sirve)."""


class SingletonClient:
    """Cliente de una sola consulta (get, set o list) contra el servidor."""

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        timeout: float = SOCKET_TIMEOUT,
    ) -> None:
        """Guarda la dirección del servidor."""
        self.host = host
        self.port = port
        self.timeout = timeout

    def request(self, request: dict[str, Any]) -> Any:
        """Envía el requerimiento y devuelve la respuesta ya decodificada."""
        logger.debug("conectando a %s:%d", self.host, self.port)
        with socket.create_connection((self.host, self.port), self.timeout) as sock:
            logger.debug("requerimiento: %s", request)
            sock.sendall(encode(request))
            raw = read_message(sock)
        if not raw.strip():
            raise ConnectionError("El servidor cerró la conexión sin responder")
        reply = decode_json(raw)
        logger.debug("respuesta: %s", reply)
        return reply


class ObserverClient:
    """Cliente suscripto: muestra cada actualización y reconecta si se corta."""

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        output: str | Path | None = None,
        retry_seconds: float = RETRY_SECONDS,
        client_uuid: str | None = None,
    ) -> None:
        """Configura destino, archivo de salida opcional y reintento."""
        self.host = host
        self.port = port
        self.output = Path(output) if output else None
        self.retry_seconds = retry_seconds
        self.client_uuid = client_uuid or str(uuid.getnode())
        self.received = 0

    def run(self, stop: threading.Event | None = None) -> int:
        """Mantiene la suscripción hasta que se pida detener; devuelve el código."""
        stop = stop or threading.Event()
        while not stop.is_set():
            try:
                self._session(stop)
            except SubscriptionRejected as exc:
                print(f"Error: {exc}", file=sys.stderr)
                return 3
            except OSError as exc:
                logger.debug("conexión perdida: %s", exc)
                self._warn(f"Servidor no disponible ({exc})")
            if stop.is_set():
                break
            self._warn(f"Reintentando en {self.retry_seconds:g} s")
            stop.wait(self.retry_seconds)
        return 0

    def _session(self, stop: threading.Event) -> None:
        """Una conexión completa: conecta, se suscribe y recibe notificaciones."""
        with socket.create_connection((self.host, self.port), SOCKET_TIMEOUT) as sock:
            sock.settimeout(0.5)
            subscribe = {"UUID": self.client_uuid, "ACTION": "subscribe"}
            sock.sendall(encode(subscribe))
            logger.debug("suscripción enviada a %s:%d", self.host, self.port)
            for line in iter_lines(sock, stop):
                try:
                    message = decode_json(line)
                except ProtocolError as exc:
                    logger.debug("mensaje descartado: %s", exc)
                    continue
                self._handle(message)
        if not stop.is_set():
            raise ConnectionError("Conexión cerrada por el servidor")

    def _handle(self, message: Any) -> None:
        """Procesa el acuse de suscripción o muestra la notificación."""
        is_ack = isinstance(message, dict) and message.get("ACTION") == "subscribe"
        if is_ack:
            if message.get("STATUS") != "OK":
                reason = message.get("ERROR", "suscripción rechazada")
                raise SubscriptionRejected(reason)
            logger.debug("suscripción confirmada")
            return
        self.received += 1
        self._emit(message)

    def _emit(self, message: Any) -> None:
        """Muestra el mensaje por salida estándar y lo agrega al archivo."""
        text = json.dumps(message, ensure_ascii=False)
        print(text, flush=True)
        if self.output is None:
            return
        try:
            with self.output.open("a", encoding="utf-8") as handle:
                handle.write(text + "\n")
        except OSError as exc:
            print(f"Error: no se puede escribir {self.output}: {exc}", file=sys.stderr)

    @staticmethod
    def _warn(text: str) -> None:
        """Informa un problema de conexión por error estándar."""
        print(text, file=sys.stderr, flush=True)
