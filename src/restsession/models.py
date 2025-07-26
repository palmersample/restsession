"""
Pydantic models used for input validation throughout this package.
When possible, break individual fields (or related fields) into their own
class. This allows granular validation of sub-fields while still allowing
a main "entry" class to be used for full model validation.
"""
# pylint: disable=no-name-in-module, no-self-argument, too-few-public-methods, line-too-long
import logging
from http import HTTPStatus
from typing import (Optional,
                    Union,
                    Annotated,
                    Callable,)
from typing_extensions import TypedDict
from pydantic import (BaseModel,
                      ConfigDict,
                      AfterValidator,
                      AnyHttpUrl,
                      NonNegativeInt,
                      NonNegativeFloat,
                      StrictBool,
                      field_validator,)
from requests.auth import AuthBase
from restsession.defaults import SESSION_DEFAULTS

logger = logging.getLogger(__name__)

# Annotated object to ensure a URL is converted to string instead of an
# "AnyHttpUrl" object.
AnyUrlString = Annotated[AnyHttpUrl, AfterValidator(str)]

class ResponseHooks(TypedDict):
    """
    Model for response hooks, allowing a list of callable functions
    """
    response: list[Callable]


class SessionParamModel(BaseModel):
    """
    RestSession parameter model.
    """
    # Always validate when a value is assigned (or updated)
    model_config = ConfigDict(validate_assignment=True,
                              arbitrary_types_allowed=True)

    base_url: Optional[AnyUrlString] = SESSION_DEFAULTS["base_url"]
    always_relative_url: StrictBool = SESSION_DEFAULTS["always_relative_url"]
    auth: Optional[Union[tuple[str, str], AuthBase]] = SESSION_DEFAULTS["auth"]
    auth_headers: Optional[list[str]] = SESSION_DEFAULTS["auth_headers"]
    backoff_factor: NonNegativeFloat = SESSION_DEFAULTS["backoff_factor"]
    headers: Optional[dict[str, str]] = SESSION_DEFAULTS["headers"]
    max_reauth: NonNegativeInt = SESSION_DEFAULTS["max_reauth"]
    max_redirects: NonNegativeInt = SESSION_DEFAULTS["max_redirects"]
    redirect_header_hook: Optional[Callable] = None
    request_exception_hook: Optional[Callable] = SESSION_DEFAULTS["request_exception_hook"]
    respect_retry_headers: StrictBool = SESSION_DEFAULTS["respect_retry_headers"]
    response_hooks: Optional[ResponseHooks] = SESSION_DEFAULTS["response_hooks"]
    retries: NonNegativeInt = SESSION_DEFAULTS["retries"]
    retry_method_list: list[str] = SESSION_DEFAULTS["retry_method_list"]
    retry_status_code_list: Union[list[NonNegativeInt], tuple[NonNegativeInt]] = SESSION_DEFAULTS["retry_status_code_list"]
    safe_arguments: StrictBool = SESSION_DEFAULTS["safe_arguments"]
    timeout: Union[NonNegativeFloat, tuple[NonNegativeFloat, NonNegativeFloat]] = SESSION_DEFAULTS["timeout"]
    tls_verify: StrictBool = SESSION_DEFAULTS["verify"]


    @field_validator("base_url")
    @classmethod
    def base_url_ends_with_slash(cls, v: Optional[AnyUrlString]) -> Optional[AnyUrlString]:
        """
        Field validator for base_url. To ensure relative URLs work as expected,
        add a trailing slash if not present.

        :param v: Value provided for base_url
        :return: Base URL with trailing slash appended
        """
        if v is not None:
            if not v.endswith("/"):
                v = f"{v}/"
        return v

    @field_validator('retry_status_code_list')
    @classmethod
    def validate_http_status_code(cls,
                                  v: Union[tuple[NonNegativeInt], list[NonNegativeInt]]
                                  ) -> list[NonNegativeInt]:
        """
        Validate that the provided status codes are valid HTTP status codes.

        :param v: Value provided for retry_status_code_list
        :return: Validated status codes as a list
        """
        if not all(code in [status.value for status in HTTPStatus] for code in v):
            raise ValueError(f"{v} is not a valid HTTP status code.")
        return v
