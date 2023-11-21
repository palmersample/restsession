"""
Define public interface imports
"""
from .newsession import RestSession
from .session_singleton import RestSessionSingleton


__all__ = [
    "RestSession",
    "RestSessionSingleton"
]
