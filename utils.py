import time
import random
import logging
import logging.handlers
import os
from typing import Callable, Any, Tuple

log = logging.getLogger("utils")
log.setLevel(logging.INFO)

# File handler (rotates at 2MB, keep 3 backups)
file_handler = logging.handlers.RotatingFileHandler(
    os.path.join(os.path.dirname(__file__), "logs", "utils.log"),
    maxBytes=2 * 1024 * 1024,
    backupCount=3,
    encoding="utf-8",
)
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
log.addHandler(file_handler)


def retry_on_exception(max_retries: int = 3, backoff_factor: float = 0.5, allowed_exceptions: Tuple[Exception, ...] = (Exception,)) -> Callable:
    """Decorator to retry a function on specified exceptions.
    
    Args:
        max_retries: Number of attempts (including the first one).
        backoff_factor: Base factor for exponential backoff. Sleep = backoff_factor * (2 ** (attempt-1)) +/- jitter.
        allowed_exceptions: Tuple of exception classes that trigger a retry.
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            attempt = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except allowed_exceptions as exc:
                    attempt += 1
                    if attempt >= max_retries:
                        log.error(f"{func.__name__} failed after {attempt} attempts: {exc}")
                        raise
                    sleep_time = backoff_factor * (2 ** (attempt - 1))
                    jitter = random.uniform(0, backoff_factor)
                    log.warning(f"Retrying {func.__name__} in {sleep_time + jitter:.2f}s (attempt {attempt}/{max_retries}) due to {exc}")
                    time.sleep(sleep_time + jitter)
        return wrapper
    return decorator
