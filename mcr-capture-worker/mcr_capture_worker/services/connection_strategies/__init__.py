# Export the models for easy access
from .abstract_connection import ConnectionStrategy
from .comu_connection import ComuConnectionStrategy
from .visio_connection import VisioStrategy
from .webconf_connection import WebConfConnectionStrategy
from .webinaire_connection import WebinaireConnectionStrategy

__all__ = [
    "ComuConnectionStrategy",
    "WebinaireConnectionStrategy",
    "ConnectionStrategy",
    "WebConfConnectionStrategy",
    "VisioStrategy",
]
