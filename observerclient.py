"""Programa ObserverClient: ``python observerclient.py {-s=host} {-p=port}``."""

import sys

from tpfi.apps.observerclient import main

if __name__ == "__main__":
    sys.exit(main())
