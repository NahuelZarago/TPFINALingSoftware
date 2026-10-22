"""Programa ObserverClient: se suscribe y muestra cada actualización."""

from __future__ import annotations

import argparse
import threading
from collections.abc import Sequence

from tpfi.cliargs import add_server_options, add_verbose, new_parser, seconds_type
from tpfi.clients import ObserverClient
from tpfi.config import EXIT_OK, RETRY_SECONDS
from tpfi.logging_setup import setup_logging


def build_parser() -> argparse.ArgumentParser:
    """Arma el parser: ``{-s=hostname} {-p=port} {-o=output.json} {-v}``."""
    parser = new_parser(
        "observerclient.py", "Recibe las actualizaciones de CorporateData."
    )
    add_server_options(parser)
    parser.add_argument(
        "-o",
        "--output",
        metavar="output.json",
        help="archivo donde agregar cada notificación (una por línea)",
    )
    parser.add_argument(
        "-r",
        "--retry",
        type=seconds_type,
        default=RETRY_SECONDS,
        metavar="seconds",
        help=f"segundos entre reintentos de conexión (por defecto {RETRY_SECONDS:g})",
    )
    add_verbose(parser)
    return parser


def main(argv: Sequence[str] | None = None, stop: threading.Event | None = None) -> int:
    """Punto de entrada; solo termina por cancelación manual o ``stop``."""
    args = build_parser().parse_args(argv)
    setup_logging(args.verbose)
    client = ObserverClient(args.server, args.port, args.output, args.retry)
    try:
        return client.run(stop)
    except KeyboardInterrupt:
        return EXIT_OK
