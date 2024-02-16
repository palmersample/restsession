"""
Pydantic models used for input validation throughout this package.
When possible, break individual fields (or related fields) into their own
class. This allows granular validation of sub-fields while still allowing
a main "entry" class to be used for full model validation.
"""
# pylint: disable=no-name-in-module, no-self-argument, too-few-public-methods, line-too-long
import logging
from typing import (Optional,
                    Union,
                    Annotated,
                    Callable)
from pydantic import (BaseModel,
                      ConfigDict,
                      AfterValidator,
                      AnyHttpUrl)
from requests.auth import AuthBase
from .defaults import SESSION_DEFAULTS

logger = logging.getLogger(__name__)

# Annotated object to ensure a URL is converted to string instead of an
# "AnyHttpUrl" object.
AnyUrlString = Annotated[AnyHttpUrl, AfterValidator(str)]


class SessionParamModel(BaseModel):
    """
    RestSession parameter model.
    """
    # Always validate when a value is assigned (or updated)
    model_config = ConfigDict(validate_assignment=True,
                              arbitrary_types_allowed=True)

    base_url: Optional[AnyUrlString] = SESSION_DEFAULTS["base_url"]
    always_relative_url: bool = SESSION_DEFAULTS["always_relative_url"]
    auth: Optional[Union[tuple[str, str], AuthBase]] = SESSION_DEFAULTS["auth"]
    auth_headers: Optional[dict[str, str]] = SESSION_DEFAULTS["auth_headers"]
    backoff_factor: float = SESSION_DEFAULTS["backoff_factor"]
    headers: Optional[dict[str, str]] = SESSION_DEFAULTS["headers"]
    max_reauth: int = SESSION_DEFAULTS["max_reauth"]
    max_redirects: int = SESSION_DEFAULTS["max_redirects"]
    redirect_header_hook: Optional[Callable] = None
    request_exception_hook: Optional[Callable] = SESSION_DEFAULTS["request_exception_hook"]
    respect_retry_headers: bool = SESSION_DEFAULTS["respect_retry_headers"]
    response_hooks: Optional[list[Callable]] = SESSION_DEFAULTS["response_hooks"]
    retries: int = SESSION_DEFAULTS["retries"]
    retry_method_list: list[str] = SESSION_DEFAULTS["retry_method_list"]
    retry_status_code_list: Union[list[int], tuple[int]] = SESSION_DEFAULTS["retry_status_code_list"]
    safe_arguments: bool = SESSION_DEFAULTS["safe_arguments"]
    timeout: Union[float, tuple[float, float]] = SESSION_DEFAULTS["timeout"]
    tls_verify: bool = SESSION_DEFAULTS["verify"]
