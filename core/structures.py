from typing import Any, Dict, List, Optional

class YIYIMailException(Exception):
    """Base exception for YIYIMail."""
    pass

class AuthenticationError(YIYIMailException):
    """Raised when login fails."""
    pass

class ConnectionError(YIYIMailException):
    """Raised when server connection fails."""
    pass

class CaseInsensitiveDict(dict):
    """
    A case-insensitive dictionary used for email headers.
    Inspired by requests.structures.CaseInsensitiveDict.
    """
    def __init__(self, data: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__()
        if data:
            for k, v in data.items():
                self[k] = v
        for k, v in kwargs.items():
            self[k] = v

    def __setitem__(self, key: str, value: Any):
        super().__setitem__(key.lower(), (key, value))

    def __getitem__(self, key: str) -> Any:
        return super().__getitem__(key.lower())[1]

    def __contains__(self, key: Any) -> bool:
        return super().__contains__(key.lower())

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def items(self):
        return (v for v in super().values())

    def keys(self):
        return (v[0] for v in super().values())

    def values(self):
        return (v[1] for v in super().values())

    def __repr__(self):
        return f"{self.__class__.__name__}({dict(self.items())!r})"
