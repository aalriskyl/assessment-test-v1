class DomainError(Exception):
    """A safe, user-facing failure with an explicit HTTP status."""

    def __init__(self, message: str, status: int = 422):
        super().__init__(message)
        self.status = status
