class NotFoundError(Exception):
    """Raised by services when a referenced record does not exist (mapped to HTTP 404)."""


class UnauthorizedError(Exception):
    """The caller is not identified (HTTP 401)."""


class ForbiddenError(Exception):
    """The caller is identified but not allowed (HTTP 403)."""


class ConflictError(Exception):
    """The request conflicts with the current state, e.g. a Strava athlete already connected to another user (HTTP 409)."""


class NotConnectedError(Exception):
    """The user has not connected a Strava account yet (HTTP 409)."""


class UpstreamError(Exception):
    """A data source (Smashrun, Strava) refused or failed. The message says why (HTTP 502)."""
