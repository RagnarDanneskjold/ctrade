

class CTradeException(Exception):
    """A base class for ctrade's exceptions."""

class CurrencyPairException(CTradeException):
    """The currency pair does not exhist."""