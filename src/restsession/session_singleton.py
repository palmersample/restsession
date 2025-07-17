"""
HTTP Session subclass definition for singleton objects. Using this class
permits an initial session object to be created with all necessary parameters
such as headers and authentication. Each subsequent invocation of the class
across modules inside a project will return the same object, reducing the
number of duplicated parameters being passed throughout functions and
methods.
"""
# pylint: disable=invalid-name
import logging
from .session import RestSession
from .metaclass import Singleton

logger = logging.getLogger(__name__)


class RestSessionSingleton(RestSession, metaclass=Singleton):
    """
    Singleton class definition. The only method override is for __exit__ to
    provide a cleanup of the _instances class attribute, effectively removing
    the singleton's existence when a context manager exits.
    """

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Cleanup - terminate the request session
        super().__exit__(exc_type, exc_val, exc_tb)

        # And set the class _instances variable to an empty dict
        RestSessionSingleton._instances = {}
