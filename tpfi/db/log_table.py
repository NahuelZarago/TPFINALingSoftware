"""Acceso físico a la tabla CorporateLog (singleton)."""

from __future__ import annotations

import logging
import platform
import uuid
from datetime import datetime, timezone
from typing import Any

from tpfi.config import LOG_KEY, LOG_TABLE
from tpfi.db.keys import discover_key
from tpfi.singleton import SingletonMeta

logger = logging.getLogger("tpfi.log")


class CorporateLogDB(metaclass=SingletonMeta):
    """Punto único de acceso a la tabla CorporateLog (pista de auditoría)."""

    def __init__(self, table: Any = None) -> None:
        """Permite inyectar una tabla (tests); si no, se crea con boto3."""
        self._table = table
        self._key_name: str | None = None

    @property
    def table(self) -> Any:
        """Devuelve la tabla DynamoDB, creándola de forma perezosa."""
        if self._table is None:
            import boto3

            dynamodb: Any = boto3.resource("dynamodb")
            self._table = dynamodb.Table(LOG_TABLE)
        return self._table

    @property
    def key_name(self) -> str:
        """Nombre de la clave de partición de la tabla."""
        if self._key_name is None:
            self._key_name = discover_key(self.table, LOG_KEY)
        return self._key_name

    def record(
        self,
        client_uuid: str,
        session: str,
        action: str,
        item_id: str | None = None,
    ) -> dict[str, Any]:
        """Registra una acción en la pista de auditoría."""
        entry: dict[str, Any] = {
            self.key_name: str(uuid.uuid4()),
            "UUID": str(client_uuid),
            "sessionid": session,
            "action": action,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "CPUid": str(uuid.getnode()),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "node": platform.node(),
        }
        if item_id:
            entry["item_id"] = item_id
        logger.debug("audit %s", entry)
        self.table.put_item(Item=entry)
        return entry
