"""Acceso físico a la tabla CorporateData (singleton)."""

from __future__ import annotations

import logging
from typing import Any

from tpfi.config import CORPORATE_FIELDS, DATA_KEY, DATA_TABLE
from tpfi.db.keys import discover_key
from tpfi.singleton import SingletonMeta

logger = logging.getLogger("tpfi.data")


class CorporateDataDB(metaclass=SingletonMeta):
    """Punto único de acceso a la tabla CorporateData (sujeto real del proxy)."""

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
            self._table = dynamodb.Table(DATA_TABLE)
        return self._table

    @property
    def key_name(self) -> str:
        """Nombre de la clave de partición de la tabla."""
        if self._key_name is None:
            self._key_name = discover_key(self.table, DATA_KEY)
        return self._key_name

    def get(self, key: str) -> dict[str, Any] | None:
        """Recupera un registro o ``None`` si no existe."""
        logger.debug("get %s", key)
        result = self.table.get_item(Key={self.key_name: key})
        item: dict[str, Any] | None = result.get("Item")
        return item

    def set(self, key: str, fields: dict[str, Any]) -> dict[str, Any]:
        """Modifica o crea un registro.

        Los campos no informados no se modifican; si el registro es nuevo
        se completan en blanco.
        """
        current = self.get(key)
        if current is None:
            current = {name: "" for name in CORPORATE_FIELDS}
        known = {k: v for k, v in fields.items() if k in CORPORATE_FIELDS}
        item = {**current, **known, self.key_name: key}
        logger.debug("set %s -> %s", key, item)
        self.table.put_item(Item=item)
        return item

    def list(self) -> list[dict[str, Any]]:
        """Devuelve todos los registros de la tabla."""
        items: list[dict[str, Any]] = []
        kwargs: dict[str, Any] = {}
        while True:
            page = self.table.scan(**kwargs)
            items.extend(page.get("Items", []))
            last = page.get("LastEvaluatedKey")
            if not last:
                return items
            kwargs["ExclusiveStartKey"] = last
