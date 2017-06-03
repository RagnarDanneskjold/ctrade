class BaseException(Exception):
    """Basic exception for errors raised."""

class CurrencyPairException(BaseException):
    """Currency pair is not available."""

class PeriodsException(BaseException):
    """Periods is not available."""

