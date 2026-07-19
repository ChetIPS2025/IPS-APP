from __future__ import annotations

import logging
import sys


def configure_logging(level_name: str = "INFO") -> None:
    root = logging.getLogger()
    level = getattr(logging, level_name.upper(), logging.INFO)
    if not root.handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
            stream=sys.stderr,
            force=False,
        )
    if level_name.upper() != "DEBUG":
        for name in ("httpx", "httpcore", "hpack"):
            logging.getLogger(name).setLevel(logging.WARNING)
