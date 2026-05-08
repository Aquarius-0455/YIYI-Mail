from .core.gateway import AirGateway
from .core.structures import AirMailException

__version__ = "1.0.0"

def connect(user, password, **kwargs):
    """
    Quick access to create a gateway instance.
    Example:
        mail = AirMail.connect('user@me.com', 'pwd')
    """
    return AirGateway(user, password, **kwargs)

__all__ = ['AirGateway', 'connect', 'AirMailException']
