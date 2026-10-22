"""Constantes de configuración del proyecto."""

from __future__ import annotations

DEFAULT_HOST = "localhost"
# Cadena vacía = escuchar en todas las interfaces (``*:8080`` según el enunciado).
DEFAULT_BIND = ""
DEFAULT_PORT = 8080
RETRY_SECONDS = 30.0
SOCKET_TIMEOUT = 10.0
MAX_MESSAGE_BYTES = 4 * 1024 * 1024

DATA_TABLE = "CorporateData"
LOG_TABLE = "CorporateLog"

# Clave de partición por defecto; si la cuenta lo permite se consulta a DynamoDB.
DATA_KEY = "id"
LOG_KEY = "id"

# Campos del tuple CorporateData (ver Tabla 1 del enunciado).
CORPORATE_FIELDS: tuple[str, ...] = (
    "id",
    "cp",
    "CUIT",
    "domicilio",
    "idreq",
    "idSeq",
    "localidad",
    "provincia",
    "sede",
    "seqID",
    "telefono",
    "web",
)

VALID_ACTIONS: tuple[str, ...] = ("get", "set", "list", "subscribe")

# Códigos de salida de los programas cliente/servidor.
EXIT_OK = 0
EXIT_UNREACHABLE = 1
EXIT_BAD_INPUT = 2
EXIT_SERVER_ERROR = 3
