"""Tipos y opciones comunes para el análisis de argumentos de los programas."""

from __future__ import annotations

import argparse

from tpfi.config import DEFAULT_HOST, DEFAULT_PORT


def port_type(value: str) -> int:
    """Convierte un argumento a puerto TCP válido (1-65535)."""
    try:
        port = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"puerto inválido: {value!r}") from None
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError(f"puerto fuera de rango (1-65535): {port}")
    return port


def seconds_type(value: str) -> float:
    """Convierte un argumento a una cantidad de segundos positiva."""
    try:
        seconds = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"segundos inválidos: {value!r}") from None
    if seconds <= 0:
        raise argparse.ArgumentTypeError(f"los segundos deben ser > 0: {seconds}")
    return seconds


def new_parser(prog: str, description: str) -> argparse.ArgumentParser:
    """Crea un parser que no acepta abreviaturas de opciones."""
    return argparse.ArgumentParser(
        prog=prog, description=description, allow_abbrev=False
    )


def add_verbose(parser: argparse.ArgumentParser) -> None:
    """Agrega la opción ``-v`` que activa los mensajes de debug."""
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="emite mensajes de debug"
    )


def add_server_options(parser: argparse.ArgumentParser) -> None:
    """Agrega las opciones ``-s`` (host) y ``-p`` (puerto) del servidor remoto."""
    parser.add_argument(
        "-s",
        "--server",
        default=DEFAULT_HOST,
        metavar="hostname",
        help=f"host del servidor (por defecto {DEFAULT_HOST})",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=port_type,
        default=DEFAULT_PORT,
        metavar="port",
        help=f"puerto del servidor (por defecto {DEFAULT_PORT})",
    )
