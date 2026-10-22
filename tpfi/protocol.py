"""Protocolo JSON: codificación, decodificación y validación de mensajes."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from tpfi.config import VALID_ACTIONS


class ProtocolError(ValueError):
    """Mensaje malformado o con datos mínimos faltantes."""


def _default(obj: Any) -> Any:
    """Serializa los Decimal que devuelve DynamoDB."""
    if isinstance(obj, Decimal):
        return int(obj) if obj == obj.to_integral_value() else float(obj)
    raise TypeError(f"No serializable: {type(obj).__name__}")


def encode(message: Any) -> bytes:
    """Codifica un mensaje como una línea JSON UTF-8 terminada en salto de línea."""
    return (json.dumps(message, default=_default, ensure_ascii=False) + "\n").encode()


def decode_json(raw: bytes | str) -> Any:
    """Decodifica texto JSON de cualquier tipo (objeto, lista o valor simple)."""
    try:
        text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        return json.loads(text)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ProtocolError(f"JSON inválido: {exc}") from exc


def decode(raw: bytes | str) -> dict[str, Any]:
    """Decodifica una línea JSON y verifica que sea un objeto."""
    data = decode_json(raw)
    if not isinstance(data, dict):
        raise ProtocolError("El mensaje debe ser un objeto JSON")
    return data


def request_id(request: dict[str, Any]) -> str | None:
    """Obtiene el ID del registro pedido (``ID``, o ``id`` como alternativa)."""
    value = request.get("ID") or request.get("id")
    return str(value) if value else None


def validate_request(request: dict[str, Any]) -> dict[str, Any]:
    """Valida los datos mínimos de un requerimiento y lo devuelve."""
    if not request.get("UUID"):
        raise ProtocolError("Falta UUID")
    action = request.get("ACTION")
    if action not in VALID_ACTIONS:
        raise ProtocolError(f"ACTION inválida: {action!r}")
    if action in ("get", "set") and not request_id(request):
        raise ProtocolError(f"La acción {action!r} requiere ID")
    return request


def response(
    request: dict[str, Any], status: str, data: Any = None, action: str | None = None
) -> dict[str, Any]:
    """Arma el mensaje de respuesta interno (sobre) para un requerimiento."""
    msg: dict[str, Any] = {
        "UUID": request.get("UUID"),
        "ACTION": action or request.get("ACTION"),
        "STATUS": status,
    }
    key = request_id(request)
    if key:
        msg["ID"] = key
    if data is not None:
        msg["DATA"] = data
    return msg


def wire_payload(reply: dict[str, Any]) -> Any:
    """Convierte la respuesta interna en lo que viaja por el socket.

    Según el enunciado, ``get`` y ``set`` responden con el registro, ``list``
    con un array de registros y cualquier falla con la indicación de error.
    El acuse de ``subscribe`` solo informa el estado.
    """
    if reply.get("STATUS") == "OK":
        if "DATA" in reply:
            return reply["DATA"]
        return {
            "UUID": reply.get("UUID"),
            "ACTION": reply.get("ACTION"),
            "STATUS": "OK",
        }
    return {
        "UUID": reply.get("UUID"),
        "ACTION": reply.get("ACTION"),
        "STATUS": "Error",
        "ERROR": reply.get("DATA"),
    }
