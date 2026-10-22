"""Descubrimiento de la clave de partición de una tabla DynamoDB."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("tpfi.keys")


def discover_key(table: Any, default: str) -> str:
    """Devuelve el nombre de la clave de partición de la tabla.

    Se consulta el esquema de la tabla; si no está disponible (permisos, tabla
    de prueba) se usa el nombre ``default``.
    """
    try:
        for attribute in table.key_schema:
            if attribute["KeyType"] == "HASH":
                return str(attribute["AttributeName"])
    except Exception as exc:  # cualquier falla de consulta cae al valor por defecto
        logger.debug("no se pudo leer key_schema (%s); uso %r", exc, default)
    return default
