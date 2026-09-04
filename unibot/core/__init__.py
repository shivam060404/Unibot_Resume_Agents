"""Core layer: state management, schema validation, and result contracts."""


class ToolError(Exception):
    """Raised inside transactional mutation functions for expected tool errors.

    The ResumeStore.transact() method catches ToolError, rolls back the
    mutation, and converts it into a standardized fail() result dict.
    Only raise for *expected* domain errors (invalid ID, bad field, etc.).
    Programmer bugs should raise normally.
    """

    def __init__(self, error_code: str, message: str, hint: str | None = None):
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.hint = hint
