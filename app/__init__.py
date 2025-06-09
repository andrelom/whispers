import os
import logging


# Get log level from environment, default to INFO if not set.
log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()

# Convert string to logging constant (e.g. "DEBUG" → logging.DEBUG).
log_level = getattr(logging, log_level_str, logging.INFO)

logging.basicConfig(
    level=log_level,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
