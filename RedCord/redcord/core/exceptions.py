class RedCordError(Exception):
    """Base application exception."""


class DatabaseUnavailableError(RedCordError):
    """Raised when database can't be reached."""


class IntegrityCheckError(RedCordError):
    """Raised when content hash verification fails."""
