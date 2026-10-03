"""The error-reporting hook shared by the long-lived worker classes.

The event bus, the Hall of Deaths, the Pet Cemetery, Bedtime and the Oracle all run
work on threads that must keep going, and each reports problems through a logger the
caller supplies (normally ``app.logger.error``). They share this one implementation so
the one rule that matters about it lives in one place.
"""

from typing import Callable, Optional


class ErrorReporting:
    """Mix in ``set_error_logger`` and ``_log_error``."""

    _error_logger: Optional[Callable[[str], None]] = None

    def set_error_logger(self, logger: Callable[[str], None]) -> None:
        """Route errors somewhere visible, normally ``app.logger.error``."""
        self._error_logger = logger

    def _log_error(self, message: str) -> None:
        """Report a problem, and never let reporting it raise."""
        if self._error_logger is not None:
            try:
                self._error_logger(message)
            except Exception:  # noqa: BLE001, S110 - reporting a failure must not fail
                # The logger is supplied by the caller and may itself be broken or
                # closed. Swallowing that here is deliberate: a failure to report a
                # problem must not become a second problem on the thread that was
                # doing the real work, and there is nowhere left to report it to.
                pass
