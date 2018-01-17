__all__ = ["DataDogMetrics"]

try:
    from doglessdata import DataDogMetrics
except ImportError:
    from .doglessdata import DataDogMetrics
