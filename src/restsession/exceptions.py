"""
Exception definitions and helper functions for restsession
"""
import logging
from string import Template

logger = logging.getLogger(__name__)


class RestSessionError(Exception):
    """
    Base Exception class for errors generated during runtime
    """


class InvalidParameterError(RestSessionError):
    """
    Exception to be raised when an parameter has been supplied with an
    invalid value - either out of bounds or of an unexpected type. If a
    Pydantic exception object is received, extract the messages, reformat,
    and use the new string as the error message
    """

    def __init__(self, err_obj):
        errmsg_template = Template("Invalid value for attribute '$field_name':\n"
                                   "  $message\n"
                                   "    expected_type: $expected_type\n"
                                   "    received_val:  $received_val\n"
                                   "    received_type: $received_type\n"
                                   "**********\n")

        def format_exception(exc_err):
            pretty_error = ("Error occurred during data validation\n"
                            "**********\n")

            for err_dict in exc_err.errors():
                pretty_error += errmsg_template.substitute(field_name=err_dict["loc"][0],
                                                           message=err_dict["msg"],
                                                           expected_type=err_dict["type"],
                                                           received_val=err_dict["input"],
                                                           received_type=type(err_dict["input"])
                                                           )
            return pretty_error

        if hasattr(err_obj, "errors"):
            error_string = format_exception(err_obj)
        else:
            error_string = err_obj

        super().__init__(error_string)


class InitializationError(RestSessionError):
    """
    Exception to be raised if there is a problem initializing the RestSession
    instance
    """
