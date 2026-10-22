"""Configuración de logging activada con el argumento ``-v``."""

from __future__ import annotations

import logging
import sys


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configura el logger raíz del proyecto.

    Con ``verbose`` se emiten mensajes DEBUG por salida estándar; de lo
    contrario solo se emiten advertencias y errores.
    """
    logger = logging.getLogger("tpfi")
    logger.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if verbose else logging.WARNING)
    logger.propagate = False
    return logger
