"""Utilidades de lectura de mensajes sobre sockets TCP."""

from __future__ import annotations

import socket
import threading
from collections.abc import Iterator

from tpfi.config import MAX_MESSAGE_BYTES
from tpfi.protocol import ProtocolError

CHUNK = 65536


def read_message(sock: socket.socket, max_bytes: int = MAX_MESSAGE_BYTES) -> bytes:
    """Lee un mensaje: hasta el primer salto de línea o hasta el cierre del par.

    Admite tanto un JSON en una línea como un JSON enviado completo seguido de
    un cierre de escritura. Falla con ``ProtocolError`` si supera ``max_bytes``.
    """
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = sock.recv(CHUNK)
        if not chunk:
            break
        newline = chunk.find(b"\n")
        if newline != -1:
            chunks.append(chunk[:newline])
            break
        chunks.append(chunk)
        total += len(chunk)
        if total > max_bytes:
            raise ProtocolError("Mensaje demasiado grande")
    return b"".join(chunks)


def iter_lines(
    sock: socket.socket, stop: threading.Event | None = None
) -> Iterator[bytes]:
    """Entrega cada línea recibida hasta que el par cierre o se pida detener.

    El socket debe tener un timeout corto para poder consultar ``stop``.
    """
    buffer = b""
    while stop is None or not stop.is_set():
        try:
            chunk = sock.recv(CHUNK)
        except TimeoutError:
            continue
        if not chunk:
            return
        buffer += chunk
        while b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            if line.strip():
                yield line
