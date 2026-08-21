class D365Error(RuntimeError):
    """Base exception for sanitized D365 integration failures."""


class D365AuthenticationError(D365Error):
    pass


class D365AuthorizationError(D365Error):
    pass


class D365RateLimitError(D365Error):
    pass


class D365UnavailableError(D365Error):
    pass


class D365MetadataError(D365Error):
    pass
