"""Programa SingletonClient: get, set o list sobre CorporateData."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from tpfi.cliargs import add_server_options, add_verbose, new_parser
from tpfi.clients import SingletonClient
from tpfi.config import EXIT_BAD_INPUT, EXIT_OK, EXIT_SERVER_ERROR, EXIT_UNREACHABLE
from tpfi.logging_setup import setup_logging
from tpfi.protocol import ProtocolError, decode


def build_parser() -> argparse.ArgumentParser:
    """Arma el parser: ``-i=input.json {-o=output.json} {-v}``."""
    parser = new_parser(
        "singletonclient.py", "Consulta o actualiza CorporateData vía el servidor."
    )
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        metavar="input.json",
        help="archivo JSON con el requerimiento",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="output.json",
        help="archivo donde grabar la respuesta (por defecto, salida estándar)",
    )
    add_server_options(parser)
    add_verbose(parser)
    return parser


def load_request(path: str) -> dict[str, Any]:
    """Lee el archivo de entrada y verifica que contenga un objeto JSON."""
    return decode(Path(path).read_bytes())


def is_error(reply: Any) -> bool:
    """Indica si la respuesta del servidor es una indicación de error."""
    return isinstance(reply, dict) and reply.get("STATUS") == "Error"


def main(argv: Sequence[str] | None = None) -> int:
    """Punto de entrada; devuelve el código de salida del proceso."""
    args = build_parser().parse_args(argv)
    setup_logging(args.verbose)
    try:
        request = load_request(args.input)
    except (OSError, ProtocolError) as exc:
        print(f"Error: no se puede usar {args.input}: {exc}", file=sys.stderr)
        return EXIT_BAD_INPUT

    client = SingletonClient(args.server, args.port)
    try:
        reply = client.request(request)
    except (OSError, ProtocolError) as exc:
        where = f"{args.server}:{args.port}"
        print(f"Error: sin respuesta del servidor {where}: {exc}", file=sys.stderr)
        return EXIT_UNREACHABLE

    text = json.dumps(reply, indent=2, ensure_ascii=False)
    if args.output:
        try:
            Path(args.output).write_text(text + "\n", encoding="utf-8")
        except OSError as exc:
            print(f"Error: no se puede escribir {args.output}: {exc}", file=sys.stderr)
            return EXIT_BAD_INPUT
    else:
        print(text)
    return EXIT_SERVER_ERROR if is_error(reply) else EXIT_OK
