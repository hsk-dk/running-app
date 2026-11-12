class NotFoundError(Exception):
    """Raised by services when a referenced record does not exist (mapped to HTTP 404)."""
