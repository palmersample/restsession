"""
Metaclass definitions

Classes in this file are not designed to be public but to supplement other
class definitions in this package.
"""


class Singleton(type):
    """
    Metaclass to return an existing instance of a class (if present) or
    initialize a new object if it's a first-time invocation.
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]
