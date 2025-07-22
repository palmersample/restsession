import pytest
from restsession.exceptions import InvalidParameterError
import logging

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.exceptions


class DummyPydanticError:
    def errors(self):
        return [
            {
                "loc": ["field1"],
                "msg": "must be an integer",
                "type": "type_error.integer",
                "input": "abc"
            },
            {
                "loc": ["field2"],
                "msg": "value too small",
                "type": "value_error.number.not_ge",
                "input": -1
            }
        ]

def test_invalid_parameter_error_with_string():
    """Test InvalidParameterError initialized with a string message."""
    err = InvalidParameterError("Simple error message")
    assert "Simple error message" in str(err)

def test_invalid_parameter_error_with_pydantic_error():
    """Test InvalidParameterError initialized with a Pydantic-like error object."""
    err_obj = DummyPydanticError()
    err = InvalidParameterError(err_obj)
    assert "field1" in str(err)
    assert "must be an integer" in str(err)
    assert "field2" in str(err)
    assert "value too small" in str(err)

def test_invalid_parameter_error_with_empty_string():
    """Test InvalidParameterError with an empty string."""
    err = InvalidParameterError("")
    assert str(err) == ""

def test_invalid_parameter_error_with_non_error_object():
    """Test InvalidParameterError with a non-error object."""
    err = InvalidParameterError(123)
    assert "123" in str(err)