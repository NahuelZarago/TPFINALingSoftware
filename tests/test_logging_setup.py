"""Tests de la configuración de logging."""

from __future__ import annotations

import logging

from tpfi.logging_setup import setup_logging


def test_verbose_enables_debug() -> None:
    assert setup_logging(True).level == logging.DEBUG


def test_default_is_quiet() -> None:
    assert setup_logging(False).level == logging.WARNING
