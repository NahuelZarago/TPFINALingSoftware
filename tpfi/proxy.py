"""Patrón Proxy: intermediario de acceso a CorporateData con auditoría."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from tpfi.db.log_table import CorporateLogDB
from tpfi.observer import SubscriptionManager
from tpfi.protocol import ProtocolError, request_id, response, validate_request
from tpfi.service import DataService

logger = logging.getLogger("tpfi.proxy")

# Claves de control del requerimiento: el resto son campos del tuple.
CONTROL_FIELDS = ("UUID", "ACTION", "SESSION", "ID")


class CorporateDataProxy:
    """Proxy de CorporateData.

    Expone la misma interfaz que el sujeto real (``DataService``) y agrega, antes
    de delegar, el registro de auditoría en CorporateLog; tras un ``set``
    notifica a los observers suscriptos.
    """

    def __init__(
        self,
        subject: DataService,
        log_db: CorporateLogDB,
        subscriptions: SubscriptionManager,
    ) -> None:
        """Recibe el sujeto real, la pista de auditoría y las suscripciones."""
        self._subject = subject
        self._log = log_db
        self._subs = subscriptions

    @property
    def subscriptions(self) -> SubscriptionManager:
        """Gestor de suscripciones (observer) asociado al proxy."""
        return self._subs

    def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        """Procesa un requerimiento JSON y devuelve la respuesta interna."""
        try:
            validate_request(request)
        except ProtocolError as exc:
            logger.debug("requerimiento inválido: %s", exc)
            return response(request, "Error", str(exc))

        action = request["ACTION"]
        client = str(request["UUID"])
        session = str(request.get("SESSION") or uuid.uuid4())
        key = request_id(request) or ""
        try:
            if action == "get":
                item = self.get(key, client=client, session=session)
                if item is None:
                    return response(request, "Error", "ID inexistente")
                return response(request, "OK", item)
            if action == "set":
                fields = {k: v for k, v in request.items() if k not in CONTROL_FIELDS}
                saved = self.set(key, fields, client=client, session=session)
                return response(request, "OK", saved)
            if action == "list":
                items = self.list(client=client, session=session)
                return response(request, "OK", items)
            self.subscribe(client=client, session=session)
            return response(request, "OK")
        except Exception as exc:  # el cliente debe recibir un error, no un corte
            logger.debug("error procesando %s: %s", action, exc)
            return response(request, "Error", str(exc))

    def _audit(
        self, client: str, session: str, action: str, key: str | None = None
    ) -> None:
        """Registra la acción en la pista de auditoría antes de ejecutarla."""
        self._log.record(client, session, action, key)

    def get(
        self, key: str, *, client: str = "unknown", session: str = ""
    ) -> dict[str, Any] | None:
        """Audita y recupera un registro."""
        self._audit(client, session, "get", key)
        return self._subject.get(key)

    def set(
        self,
        key: str,
        fields: dict[str, Any],
        *,
        client: str = "unknown",
        session: str = "",
    ) -> dict[str, Any]:
        """Audita, modifica un registro y notifica a los suscriptos."""
        self._audit(client, session, "set", key)
        item = self._subject.set(key, fields)
        delivered = self._subs.notify(item)
        logger.debug("set %s notificado a %d observers", key, delivered)
        return item

    def subscribe(self, *, client: str = "unknown", session: str = "") -> None:
        """Audita una suscripción (el socket lo registra el servidor)."""
        self._audit(client, session, "subscribe")

    def list(
        self, *, client: str = "unknown", session: str = ""
    ) -> list[dict[str, Any]]:
        """Audita y devuelve todos los registros."""
        self._audit(client, session, "list")
        return self._subject.list()
