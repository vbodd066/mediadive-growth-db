"""
mediadive-growth-db
~~~~~~~~~~~~~~~~~~~

ML pipeline for predicting and generating viable microbial growth media.
"""

import logging
import sys

from src.config import LOG_LEVEL

# ── Package-level logger ────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(name)-28s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)

logger = logging.getLogger("mediadive")
