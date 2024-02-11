"""
Pydantic models used for input validation throughout this package.
When possible, break individual fields (or related fields) into their own
class. This allows granular validation of sub-fields while still allowing
a main "entry" class to be used for full model validation.
"""
# pylint: disable=no-name-in-module, no-self-argument, too-few-public-methods
import logging
from typing import (Optional,
                    Union,
                    Callable)
from dataclasses import dataclass
from pydantic import (BaseModel,
                      AnyHttpUrl,
                      StrictBool,
                      StrictFloat,
                      StrictInt,
                      StrictStr,
                      # ValidationError,
                      conint,
                      conlist,
                      # parse_obj_as,
                      # validator,
                      field_validator,
                      TypeAdapter,
                      ConfigDict)
from requests.auth import AuthBase
from requests.cookies import RequestsCookieJar
from .defaults import SESSION_DEFAULTS
# from .default_hooks import (remove_custom_auth_header_on_redirect,
#                             default_request_exception_hook)

logger = logging.getLogger(__name__)


class TimeoutValidator(BaseModel):
    """
    Model for HTTP request timeout value
    """
    timeout: Union[StrictInt, StrictFloat]


class RetriesValidator(BaseModel):
    """
    Model for HTTP request number of retries
    """
    retries: StrictInt


class MaxRedirectValidator(BaseModel):
    """
    Model for HTTP request max redirect count
    """
    max_redirects: StrictInt


class BackoffFactorValidator(BaseModel):
    """
    Model for HTTP retry backoff factor
    """
    backoff_factor: Union[StrictInt, StrictFloat]


class RetryStatusCodeListValidator(BaseModel):
    """
    Model for HTTP request retry status code list. Accepted codes for retries
    in this model are as follows:

        1xx (Informational) - None - No reason to retry
        2xx (Success) - None - No reason to retry
        3xx (Redirection) - None - handled by max_redirect
        429 (Too Many Requests) - Accepted and recommended
        4xx (not 429) - None - Client errors - correct the request
        5xx (Server Errors) - Any acceptable for retry
    """
    retry_status_code_list: list[conint(strict=True, ge=300, le=599)]


class RetryMethodListValidator(BaseModel):
    """
    Model for HTTP methods permitted for retry operations. Default list from
    urllib3 includes:
        - DELETE
        - GET
        - HEAD
        - OPTIONS
        - PUT
        - TRACE

    Other methods may be added without restriction, including custom HTTP
    methods.
    """
    retry_method_list: list[str]


class RespectRetryHeadersValidator(BaseModel):
    """
    Model for HTTP request Retry-After header response handling
    """
    respect_retry_headers: StrictBool


class BaseUrlValidator(BaseModel):
    """
    Model for HTTP Base URL definition
    """
    base_url: Optional[str]

    @field_validator("base_url")
    @classmethod
    def base_url_must_be_a_url(cls, url_val: str):
        url_validator = TypeAdapter(AnyHttpUrl)
        if url_val is not None and not url_validator.validate_python(url_val):
            raise ValueError(f"Invalid URL '{url_val}' specified for base_url")
        return url_val


class TlsVerifyValidator(BaseModel):
    """
    Model for HTTPS TLS Certificate Chain Validation
    """
    tls_verify: StrictBool


class UsernameValidator(BaseModel):
    """
    Model for HTTP Basic Authentication - Username
    """
    username: Optional[StrictStr]


class PasswordValidator(BaseModel):
    """
    Model for HTTP Basic Authentication - Password
    """
    password: Optional[StrictStr]


class AuthValidator(BaseModel):
    """
    Model for HTTP Basic Authentication - Password
    """
    auth: Optional[Union[tuple[str, str], AuthBase]]

    class Config:
        """
        pydantic configuration options for AuthValidator.
        """
        arbitrary_types_allowed = True


class MaxReauthValidator(BaseModel):
    """
    Model for HTTP request number of retries
    """
    max_reauth: StrictInt = SESSION_DEFAULTS["max_reauth"]


class RedirectHeaderHookValidator(BaseModel):
    """
    Model for the request exception hook
    """
    redirect_header_hook: Optional[conlist(Callable,
                                           min_length=0,
                                           max_length=1)] = SESSION_DEFAULTS["redirect_header_hook"]


class RequestExceptionHookValidator(BaseModel):
    """
    Model for the request exception hook
    """
    request_exception_hook: Optional[
        conlist(
            Callable,
            min_length=0,
            max_length=1
        )
    ] = SESSION_DEFAULTS["request_exception_hook"]


class ResponseHookValidator(BaseModel):
    """
    Model for HTTP Basic Authentication - Password
    """
    response_hooks: Optional[list[Callable]] = SESSION_DEFAULTS["response_hooks"]


class SessionHeaderValidator(BaseModel):
    """
    Model for HTTP header validation. Make sure the input is a dict and, if
    not null, that the k/v pairs are strings.
    """
    headers: Optional[dict[str, str]]
    auth_headers: Optional[dict[str, str]]


# pylint: disable-next=too-many-ancestors, too-many-instance-attributes
class HttpSessionArguments(ResponseHookValidator,
                           MaxReauthValidator,
                           AuthValidator,
                           PasswordValidator,
                           UsernameValidator,
                           TlsVerifyValidator,
                           BaseUrlValidator,
                           RespectRetryHeadersValidator,
                           RetryMethodListValidator,
                           RetryStatusCodeListValidator,
                           BackoffFactorValidator,
                           MaxRedirectValidator,
                           RetriesValidator,
                           TimeoutValidator,
                           SessionHeaderValidator,
                           RequestExceptionHookValidator,
                           RedirectHeaderHookValidator
                           ):
    model_config = ConfigDict(validate_assignment=True,
                              arbitrary_types_allowed=True)

    """
    Validate all session arguments by inheriting each individual BaseModel
    class.
    """


class SessionParamModel(BaseModel):
    # Always validate when a value is assigned (or updated)
    model_config = ConfigDict(validate_assignment=True,
                              arbitrary_types_allowed=True)

    headers: Optional[dict[str, str]] = SESSION_DEFAULTS["headers"]
    auth_headers: dict = SESSION_DEFAULTS["auth_headers"]
    timeout: Union[float, tuple[float, float]] = SESSION_DEFAULTS["timeout"]
    retries: int = SESSION_DEFAULTS["retries"]
    max_redirects: int = SESSION_DEFAULTS["max_redirects"]
    backoff_factor: float = SESSION_DEFAULTS["backoff_factor"]
    retry_status_code_list: Union[list[int], tuple[int]] = SESSION_DEFAULTS["retry_status_code_list"]
    retry_method_list: list[str] = SESSION_DEFAULTS["retry_method_list"]
    respect_retry_headers: bool = SESSION_DEFAULTS["respect_retry_headers"]
    base_url: Optional[str] = SESSION_DEFAULTS["base_url"]
    tls_verify: bool = SESSION_DEFAULTS["verify"]
    auth: Optional[Union[tuple[str, str], AuthBase]] = SESSION_DEFAULTS["auth"]
    max_reauth: int = SESSION_DEFAULTS["max_reauth"]
    redirect_header_hook: Optional[Callable] = None
    response_hooks: Optional[list[Callable]] = SESSION_DEFAULTS["response_hooks"]
    request_exception_hook: Optional[Callable] = SESSION_DEFAULTS["request_exception_hook"]
    safe_arguments: bool = SESSION_DEFAULTS["safe_arguments"]
    always_relative_url: bool = SESSION_DEFAULTS["always_relative_url"]

    @field_validator("base_url")
    @classmethod
    def base_url_must_be_a_url(cls, url_val: str):
        url_validator = TypeAdapter(AnyHttpUrl)
        if url_val is not None and not url_validator.validate_python(url_val):
            raise ValueError(f"Invalid URL '{url_val}' specified for base_url")
        return url_val

@dataclass
class SessionParameters:  # pylint: disable=too-many-instance-attributes
    headers: dict
    auth_headers: dict
    timeout: float
    retries: int
    max_redirects: int
    backoff_factor: float
    retry_status_code_list: Union[list[int], tuple[int]]
    retry_method_list: list[str]
    respect_retry_headers: bool
    base_url: Optional[str]
    tls_verify: bool
    username: str
    password: str
    auth: Optional[Union[tuple[str, str], AuthBase]]
    max_reauth: int
    redirect_header_hook: Optional[list[Callable]]
    request_exception_hook: Optional[list[Callable]]
    response_hooks: Optional[list[Callable]]

class NewSessionParamModel(BaseModel):
    # Always validate when a value is assigned (or updated)
    model_config = ConfigDict(validate_assignment=True,
                              arbitrary_types_allowed=True)

    headers: Optional[dict[str, str]]
    auth_headers: Optional[dict[str, str]]
    timeout: float
    retries: StrictInt
    max_redirects: StrictInt
    backoff_factor: Union[StrictInt, StrictFloat]
    retry_status_code_list: list[conint(strict=True, ge=300, le=599)]
    retry_method_list: list[str]
    respect_retry_headers: StrictBool
    base_url: Optional[str]
    tls_verify: StrictBool
    username: Optional[StrictStr]
    password: Optional[StrictStr]
    auth: Optional[Union[tuple[str, str], AuthBase]]
    max_reauth: StrictInt
    cookies: Optional[RequestsCookieJar] = None
    redirect_header_hook: Optional[conlist(Callable,
                                           min_length=0,
                                           max_length=1)]
    request_exception_hook: Optional[conlist(Callable,
                                             min_length=0,
                                             max_length=1)]
    response_hooks: Optional[list[Callable]]

    @field_validator("base_url")
    @classmethod
    def base_url_must_be_a_url(cls, url_val: str):
        url_validator = TypeAdapter(AnyHttpUrl)
        if url_val is not None and not url_validator.validate_python(url_val):
            raise ValueError(f"Invalid URL '{url_val}' specified for base_url")
        return url_val
