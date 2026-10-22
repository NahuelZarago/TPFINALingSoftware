"""Servidor TCP que expone el proxy de CorporateData a los clientes."""

from __future__ import annotations

import logging
import os
import socket
import threading
from typing import Any

from tpfi.config import DEFAULT_BIND, DEFAULT_PORT, SOCKET_TIMEOUT
from tpfi.net import read_message
from tpfi.observer import SocketObserver
from tpfi.protocol import ProtocolError, decode, encode, wire_payload
from tpfi.proxy import CorporateDataProxy

logger = logging.getLogger("tpfi.server")


class ServerStartError(RuntimeError):
    """No se pudo abrir el puerto de escucha (por ejemplo, ya está en uso)."""


class ProxyServer:
    """Servidor de aplicaciones: un hilo por conexión entrante.

    ``get``, ``set`` y ``list`` se responden y se cierra la conexión;
    ``subscribe`` deja el socket abierto y registrado como observer.
    """

    def __init__(
        self,
        proxy: CorporateDataProxy,
        host: str = DEFAULT_BIND,
        port: int = DEFAULT_PORT,
    ) -> None:
        """Configura el servidor; no abre el puerto hasta ``start``."""
        self._proxy = proxy
        self._host = host
        self._port = port
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    @property
    def port(self) -> int:
        """Puerto efectivo de escucha (útil cuando se pidió el puerto 0)."""
        if self._sock is not None:
            return int(self._sock.getsockname()[1])
        return self._port

    def start(self) -> None:
        """Abre el puerto y comienza a aceptar conexiones en segundo plano."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if os.name != "nt":
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((self._host, self._port))
            sock.listen()
        except OSError as exc:
            sock.close()
            where = f"{self._host or '*'}:{self._port}"
            raise ServerStartError(f"No se puede escuchar en {where}: {exc}") from exc
        sock.settimeout(0.5)
        self._sock = sock
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._accept_loop, args=(sock,), daemon=True, name="accept"
        )
        self._thread.start()
        logger.debug("escuchando en %s:%d", self._host or "*", self.port)

    def serve_forever(self, stop: threading.Event | None = None) -> None:
        """Atiende hasta que se llame a ``stop`` o se active el evento dado."""
        if self._thread is None:
            self.start()
        try:
            while not self._stop.is_set() and not (stop is not None and stop.is_set()):
                self._stop.wait(0.2)
        finally:
            self.stop()

    def stop(self) -> None:
        """Deja de aceptar conexiones y cierra a los suscriptores."""
        self._stop.set()
        sock, self._sock = self._sock, None
        if sock is not None:
            sock.close()
        thread, self._thread = self._thread, None
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2.0)
        self._proxy.subscriptions.close_all()

    def _accept_loop(self, sock: socket.socket) -> None:
        """Acepta conexiones y lanza un hilo por cada una."""
        while not self._stop.is_set():
            try:
                conn, addr = sock.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            logger.debug("conexión de %s", addr)
            threading.Thread(
                target=self._serve_client, args=(conn,), daemon=True
            ).start()

    def _serve_client(self, conn: socket.socket) -> None:
        """Atiende una conexión: lee el requerimiento, responde y cierra."""
        keep_open = False
        try:
            conn.settimeout(SOCKET_TIMEOUT)
            request = decode(read_message(conn))
            reply = self._proxy.handle(request)
            payload = wire_payload(reply)
            subscribed = request.get("ACTION") == "subscribe"
            if reply.get("STATUS") == "OK" and subscribed:
                keep_open = self._register(request, conn, payload)
            else:
                conn.sendall(encode(payload))
        except ProtocolError as exc:
            self._reply_error(conn, str(exc))
        except OSError as exc:
            logger.debug("conexión con el cliente interrumpida: %s", exc)
        finally:
            if not keep_open:
                conn.close()

    def _register(self, request: dict[str, Any], conn: socket.socket, ack: Any) -> bool:
        """Envía el acuse y registra el socket como observer."""
        observer = SocketObserver(str(request["UUID"]), conn)
        if not observer.update(ack):
            return False
        self._proxy.subscriptions.attach(observer)
        logger.debug("suscripto %s", observer.uuid)
        return True

    @staticmethod
    def _reply_error(conn: socket.socket, message: str) -> None:
        """Informa un requerimiento inválido sin propagar fallos de red."""
        try:
            conn.sendall(encode({"STATUS": "Error", "ERROR": message}))
        except OSError as exc:
            logger.debug("no se pudo informar el error: %s", exc)
