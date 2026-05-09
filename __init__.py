from .core.gateway import YIYIGateway
from .core.structures import YIYIMailException
from .core.utils import show, save, load

__version__ = "1.0.3"

def connect(user, password, **kwargs):
    """
    Quick access to create a gateway instance.
    Example:
        mail = YIYIMail.connect('user@me.com', 'pwd')
    """
    return YIYIGateway(user, password, **kwargs)

__all__ = ['YIYIGateway', 'connect', 'YIYIMailException', 'show', 'save', 'load']
