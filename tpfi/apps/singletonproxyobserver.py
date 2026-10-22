"""Programa servidor SingletonProxyObserverTPFI."""

from __future__ import annotations

import argparse
import sys
import threading
from collections.abc import Sequence

from tpfi.cliargs import add_verbose, new_parser, port_type
from tpfi.config import DEFAULT_BIND, DEFAULT_PORT, EXIT_OK, EXIT_UNREACHABLE
from tpfi.db.data_table import CorporateDataDB
from tpfi.db.log_table import CorporateLogDB
from tpfi.logging_setup import setup_logging
from tpfi.observer import SubscriptionManager
from tpfi.proxy import CorporateDataProxy
from tpfi.server import ProxyServer, ServerStartError


def build_parser() -> argparse.ArgumentParser:
    """Arma el parser: ``{-p=port} {-v}``."""
    parser = new_parser("singletonproxyobserver.py", "Servidor proxy de CorporateData.")
    parser.add_argument(
        "-p",
        "--port",
        type=port_type,
        default=DEFAULT_PORT,
        metavar="port",
        help=f"puerto de escucha (por defecto *:{DEFAULT_PORT})",
    )
    add_verbose(parser)
    return parser


def build_proxy() -> CorporateDataProxy:
    """Ensambla el proxy con los singletons de acceso a DynamoDB."""
    return CorporateDataProxy(
        CorporateDataDB(), CorporateLogDB(), SubscriptionManager()
    )


def main(
    argv: Sequence[str] | None = None,
    proxy: CorporateDataProxy | None = None,
    stop: threading.Event | None = None,
) -> int:
    """Punto de entrada; solo termina por cancelación manual o ``stop``."""
    args = build_parser().parse_args(argv)
    setup_logging(args.verbose)
    server = ProxyServer(proxy or build_proxy(), DEFAULT_BIND, args.port)
    try:
        server.start()
    except ServerStartError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_UNREACHABLE
    print(f"Servidor escuchando en *:{server.port}", flush=True)
    try:
        server.serve_forever(stop)
    except KeyboardInterrupt:
        server.stop()
    return EXIT_OK
