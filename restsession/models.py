"""
Pydantic models used for input validation throughout this package.
When possible, break individual fields (or related fields) into their own
class. This allows granular validation of sub-fields while still allowing
a main "entry" class to be used for full model validation.
"""
# pylint: disable=no-name-in-module, no-self-argument, too-few-public-methods
import logging
from typing import (Optional,
                    Union)
from pydantic import (BaseModel,
                      AnyHttpUrl,
                      StrictBool,
                      StrictFloat,
                      StrictInt,
                      StrictStr,
                      ValidationError,
                      conint,
                      parse_obj_as,
                      validator)
from requests.auth import AuthBase
from .defaults import SESSION_DEFAULTS

logger = logging.getLogger(__name__)


class TimeoutValidator(BaseModel):
    """
    Model for HTTP request timeout value
    """
    timeout: StrictInt = None

    @validator("timeout", pre=True)
    def validate_timeout(cls, value):
        """
        Validate the requested timeout value. If not an integer or if no
        value supplied, return the default value for timeout.

        :param value: Value provided (or None if no value)
        :return: Either the requested timeout value or a default
        """
        result = SESSION_DEFAULTS["timeout"]
        logger.debug("Validating supplied timeout value: %s", value)
        try:
            parse_obj_as(StrictInt, value)
        except ValidationError:
            pass
        else:
            result = value
        logger.debug("Returning timeout value: %s", result)
        return result


class RetriesValidator(BaseModel):
    """
    Model for HTTP request number of retries
    """
    retries: StrictInt = None

    @validator("retries", pre=True)
    def validate_retries(cls, value):
        """
        Validate the requested retry count. If not an integer or if no
        value supplied, return the default value.

        :param value: Value provided (or None if no value)
        :return: Either the requested retry value or a default
        """
        result = SESSION_DEFAULTS["retries"]
        logger.debug("Validating supplied retry value: %s", value)
        try:
            parse_obj_as(StrictInt, value)
        except ValidationError:
            pass
        else:
            result = value
        logger.debug("Returning retry value: %s", result)
        return result


class MaxRedirectValidator(BaseModel):
    """
    Model for HTTP request max redirect count
    """
    max_redirect: StrictInt = None

    @validator("max_redirect", pre=True)
    def validate_max_redirect(cls, value):
        """
        Validate the requested max_redirect value. If not an integer or if no
        value supplied, return the default value.

        :param value: Value provided (or None if no value)
        :return: Either the requested max redirect value or a default
        """
        result = SESSION_DEFAULTS["max_redirect"]
        logger.debug("Validating supplied max_redirect value: %s", value)
        try:
            parse_obj_as(StrictInt, value)
        except ValidationError:
            pass
        else:
            result = value
        logger.debug("Returning max_redirect value: %s", result)
        return result


class BackoffFactorValidator(BaseModel):
    """
    Model for HTTP retry backoff factor
    """
    backoff_factor: StrictFloat = None

    @validator("backoff_factor", pre=True)
    def validate_backoff_factor(cls, value):
        """
        Validate the requested backoff factor. If not a float or if no
        value supplied, return the default value.

        :param value: Value provided (or None if no value)
        :return: Either the requested backoff factor or a default
        """
        result = SESSION_DEFAULTS["backoff_factor"]
        logger.debug("Validating supplied backoff_factor value: %s", value)
        try:
            parse_obj_as(StrictFloat, value)
        except ValidationError:
            pass
        else:
            result = value
        logger.debug("Returning backoff_factor value: %s", result)
        return result


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
    retry_status_code_list: list[conint(strict=True, ge=300, le=599)] = []
    #     Union[
    #         conint(strict=True, ge=301, le=301),
    #         conint(strict=True, ge=429, le=429),
    #         conint(strict=True, ge=500, le=599)
    #     ]
    # ] = []

    # pylint: disable=loop-invariant-statement
    @validator("retry_status_code_list", pre=True)
    def validate_retry_status_code_list(cls, value):
        """
        Validate the requested retry status code list. If an invalid status
        code is supplied, omit that from the resulting list. Otherwise,
        return the requested values OR the default values (if no list supplied)

        :param value: Value provided (or None if no value)
        :return: Validated retry status code list or the default
        """
        default_result = SESSION_DEFAULTS["retry_status_codes"]
        logger.debug("Validating supplied retry_status_code_list: %s", value)
        validated_codes = None

        if isinstance(value, list):
            validated_codes = [supplied_code for supplied_code in value
                               if isinstance(supplied_code, int)
                               and supplied_code in [*range(300, 599)]
                               ]

        logger.debug("Returning retry_status_code_list value: %s",
                     validated_codes or default_result)
        return validated_codes or default_result


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
    retry_method_list: list[str] = []

    @validator("retry_method_list", pre=True)
    def validate_retry_method_list(cls, value):
        """
        Validate the requested retry methods. Any method is permitted due
        to the potential for custom methods on a given API. If no values
        are supplied, return the default.

        :param value: Value provided (or None if no value)
        :return: Either the requested retry methods or the default
        """
        default_result = SESSION_DEFAULTS["retry_methods"]
        logger.debug("Validating supplied retry_method_list: %s", value)
        retry_methods = None
        if isinstance(value, list):
            retry_methods = [supplied_method.upper() for supplied_method in value
                             if isinstance(supplied_method, str)
                             ]
        logger.debug("Returning retry_method_list value: %s", retry_methods or default_result)
        return retry_methods or default_result


class RespectRetryHeadersValidator(BaseModel):
    """
    Model for HTTP request Retry-After header response handling
    """
    respect_retry_headers: StrictBool = None

    @validator("respect_retry_headers", pre=True)
    def validate_respect_retry_headers(cls, value):
        """
        Validate the requested value for the respect_retry_headers parameter.
        If a non-boolean result is provided, return the default (True)

        :param value: Value provided (or None if no value)
        :return: Either the requested boolean or True if invalid/missing
        """
        result = SESSION_DEFAULTS["respect_retry_headers"]
        logger.debug("Validating respect_retry_headers value: %s", value)
        try:
            parse_obj_as(StrictBool, value)
        except ValidationError:
            pass
        else:
            result = value
        logger.debug("Returning respect_retry_headers value: %s", result)
        return result


class BaseUrlValidator(BaseModel):
    """
    Model for HTTP Base URL definition
    """
    base_url: Optional[AnyHttpUrl] = None

    @validator("base_url", pre=True)
    def validate_base_url(cls, value):
        """
        Validate the requested Base URL. If the parameter is not a valid URL
        including the scheme (http or https), return None.

        :param value: Value provided (or None if no value)
        :return: Validated base URL or None if invalid/missing
        """
        result = SESSION_DEFAULTS["base_url"]
        logger.debug("Validating supplied base_url value: %s", value)
        try:
            parse_obj_as(AnyHttpUrl, value)
        except ValidationError:
            pass
        else:
            result = value
        logger.debug("Returning base_url value: %s", result)
        return result


class TlsVerifyValidator(BaseModel):
    """
    Model for HTTPS TLS Certificate Chain Validation
    """
    tls_verify: StrictBool = None

    @validator("tls_verify", pre=True)
    def validate_tls_verify(cls, value):
        """
        Validate the requested TLS chain verification setting. If invalid
        (non-boolean) or missing, return the default

        :param value: Value provided (or None if no value)
        :return: Requested TLS validation setting or True if missing/invalid
        """
        result = SESSION_DEFAULTS["tls_verify"]
        logger.debug("Validating supplied tls_verify value %s", value)
        try:
            parse_obj_as(StrictBool, value)
        except ValidationError:
            pass
        else:
            result = value
        logger.debug("Returning tls_verify value: %s", result)
        return result


class UsernameValidator(BaseModel):
    """
    Model for HTTP Basic Authentication - Username
    """
    username: Optional[StrictStr] = None

    @validator("username", pre=True)
    def validate_username(cls, value):
        """
        Validate the username is a string.

        :param value: Value provided (or None if no value)
        :return: Username or None if invalid data type
        """
        result = SESSION_DEFAULTS["username"]
        logger.debug("Validating supplied username value %s", value)
        try:
            parse_obj_as(StrictStr, value)
        except ValidationError:
            pass
        else:
            result = value
        logger.debug("Returning username value: %s", result)
        return result


class PasswordValidator(BaseModel):
    """
    Model for HTTP Basic Authentication - Password
    """
    password: Optional[StrictStr] = None

    @validator("password", pre=True)
    def validate_password(cls, value):
        """
        Validate the password is a string.

        :param value: Value provided (or None if no value)
        :return: Password or None if invalid data type
        """
        result = SESSION_DEFAULTS["password"]
        logger.debug("Validating supplied password value ...")
        try:
            parse_obj_as(StrictStr, value)
        except ValidationError:
            pass
        else:
            result = value
        logger.debug("Returning password value ...")
        return result


class AuthValidator(BaseModel):
    """
    Model for HTTP Basic Authentication - Password
    """
    auth: Optional[Union[tuple[str, str], AuthBase]] = None

    class Config:
        arbitrary_types_allowed = True

    @validator("auth", pre=True)
    def validate_auth(cls, value):
        """
        Validate the auth attribute is a tuple of strings or an instance
        of requests.auth.AuthBase

        :param value: Value provided (or None if no value)
        :return: Auth method or None if invalid data type
        """
        result = None
        logger.debug("Validating supplied auth method ...")
        try:
            if isinstance(value, tuple):
                if len(value) == 2 \
                        and isinstance(value[0], str) \
                        and isinstance(value[1], str):
                    result = value
            elif isinstance(value, AuthBase):
                result = value
        except ValidationError:
            pass
        logger.debug("Returning auth value ...")
        return result


class MaxReauthValidator(BaseModel):
    """
    Model for HTTP request number of retries
    """
    max_reauth: StrictInt = None

    @validator("max_reauth", pre=True)
    def validate_max_reauth(cls, value):
        """
        Validate the requested max reauth count. If not an integer or if no
        value supplied, return the default value.

        :param value: Value provided (or None if no value)
        :return: Either the requested retry value or a default
        """
        result = SESSION_DEFAULTS["max_reauth"]
        logger.debug("Validating supplied max_reauth value: %s", value)
        try:
            parse_obj_as(StrictInt, value)
        except ValidationError:
            pass
        else:
            result = value
        logger.debug("Returning max_reauth value: %s", result)
        return result


class ResponseHookValidator(BaseModel):
    """
    Model for HTTP Basic Authentication - Password
    """
    response_hooks: Optional[list] = []


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
                           TimeoutValidator
                           ):
    """
    Validate all session arguments by inheriting each individual BaseModel
    class.
    """
