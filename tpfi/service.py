"""Interfaz común del sujeto real y del proxy (patrón Proxy)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class DataService(Protocol):
    """Operaciones sobre CorporateData que comparten el sujeto real y el proxy."""

    def get(self, key: str) -> dict[str, Any] | None:
        """Recupera un registro o ``None`` si no existe."""
        ...

    def set(self, key: str, fields: dict[str, Any]) -> dict[str, Any]:
        """Modifica o crea un registro y lo devuelve."""
        ...

    def list(self) -> list[dict[str, Any]]:
        """Devuelve todos los registros."""
        ...
