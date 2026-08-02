class PermanentError(Exception):
    """Exception raised when an execution error is permanent and should not be retried."""
    pass

class TransientError(Exception):
    """Exception raised when an execution error is temporary and can be retried."""
    pass
