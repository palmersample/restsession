"""
Base class definitions for HTTP Session, including properties and setter
methods.

Keyword parameter validation is performed via Pydantic models to simplify
instantiation and ensure a valid session is available, even if an incorrect
parameter is supplied.
"""
import logging
from typing import Any, Optional, Union
from types import MappingProxyType
from urllib.parse import urlparse
from requests.exceptions import (HTTPError as RequestHTTPError,
                                 ConnectionError as RequestConnectionError,
                                 InvalidJSONError as RequestInvalidJSONError,
                                 Timeout as RequestTimeout,
                                 MissingSchema as RequestMissingSchema,
                                 RetryError as RequestRetryError,
                                 TooManyRedirects as RequestTooManyRedirects,
                                 RequestException)
from requests.adapters import HTTPAdapter
from requests.auth import AuthBase
from requests_toolbelt import sessions
from urllib3 import disable_warnings
from urllib3.util.retry import Retry
from .defaults import SESSION_DEFAULTS
from .default_hooks import (remove_custom_auth_header_on_redirect, default_request_exception_hook)
from .models import (
    HttpSessionArguments,
    TimeoutValidator,
    RetriesValidator,
    MaxRedirectValidator,
    BackoffFactorValidator,
    RetryStatusCodeListValidator,
    RetryMethodListValidator,
    RespectRetryHeadersValidator,
    BaseUrlValidator,
    TlsVerifyValidator,
    UsernameValidator,
    PasswordValidator,
    AuthValidator
)

logger = logging.getLogger(__name__)


class TimeoutHTTPAdapter(HTTPAdapter):
    """
    Extends the HTTPAdapter class to set a timeout for requests Session
    objects.  When used for a session, set the timeout to the value of
    REQUEST_TIMEOUT by default.  This will be overridden if the
    'timeout' argument is supplied.
    """
    def __init__(self, *args, **kwargs):
        if "timeout" in kwargs:
            self.timeout = kwargs["timeout"]
            del kwargs["timeout"]
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        # pylint: disable=arguments-differ
        timeout = kwargs.get('timeout')
        if timeout is None:
            kwargs["timeout"] = self.timeout
        return super().send(request, **kwargs)


# def default_request_exception_hook(response, **kwargs):  # pylint: disable=unused-argument
#     """
#     This function is bound to the HTTP Session object and raises the request
#     Response for status, catches exceptions, and re-raises the same exception
#     to be handled by the calling script. This avoids having to repeat the
#     raise_for_status() method each time a request is made by the caller.
#
#     The response hook can be overridden during or after class instantiation
#     to permit app-specific custom exception raises.
#
#     :param response: Requests response object
#     :return: None
#     """
#
#     try:
#         response.raise_for_status()
#     except RequestTooManyRedirects as err:
#         logger.error("Too many redirects occurred when processing the request: %s", err)
#         raise RequestTooManyRedirects(err) from err
#     except RequestRetryError as err:
#         logger.error("Request retry handler error was encountered: %s", err)
#         # raise RequestRetryError(err) from err
#         raise RequestTooManyRedirects(err) from err
#     except RequestTimeout as err:
#         logger.error("The HTTP request timed out: %s", err)
#         raise RequestTimeout(err) from err
#     except RequestConnectionError as err:
#         logger.error("A connection error occurred while processing the request: %s", err)
#         raise RequestConnectionError(err) from err
#     except RequestHTTPError as err:
#         logger.error("Error performing HTTP request: %s", err)
#         raise RequestHTTPError(err) from err
#     except RequestInvalidJSONError as err:
#         logger.error("An error occurred processing JSON for the request: %s", err)
#         raise RequestInvalidJSONError(err) from err
#     except RequestMissingSchema as err:
#         logger.error("Missing scheme in request. "
#                      "Check that base_url is set if using relative path: %s", err)
#         raise RequestMissingSchema(err) from err
#     except RequestException as err:
#         logger.error("An unspecified request exception was encountered: %s", err)
#         raise RequestException(err) from err
#
#
# def remove_custom_auth_header_on_redirect(headers: Optional[list[str]] = ()):
#     """
#     Given a list of header keys, if any are present after a cross-domain
#     redirect they will be removed. The "Authorization" header is already
#     handled by the requests library, so this permits custom auth headers
#     to also be removed for security reasons.
#
#     The returned function (redirect_header_hook) will be the first response
#     hook attached to the Session object.
#
#     :param headers: List of header names to remove on redirect
#     :return: redirect_header_hook function reference to be used as a hook
#     """
#     def redirect_header_hook(response, **kwargs):  # pylint: disable=unused-argument
#         """
#         Hook used when a redirect response is received. If redirected to a
#         different host, remove any custom auth headers as supplied in the
#         wrapping function.
#
#         :param response: requests Response object
#         :param kwargs: Any arguments passed to the response hook by requests
#         :return: None
#         """
#         if response.is_redirect and headers and \
#                 (urlparse(response.request.url).netloc !=
#                  urlparse(response.headers["Location"]).netloc):
#
#             # Only strip the headers when being redirected to a different host
#             response.request.headers = {
#                 k: v for k, v in response.request.headers.items() if k not in headers
#             }
#
#     return redirect_header_hook


class RestSession:
    """
    Main HTTP Session class. On init, create a new HTTP base URL session for the
    object, generate all needed settings for timeout/retries and configure
    HTTP Basic authentication if a username/password is provided.
    """
    # pylint: disable=too-many-arguments
    # pylint: disable=unused-argument
    # pylint: disable=too-many-public-methods
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-locals
    def __init__(self,
                 headers: dict = SESSION_DEFAULTS["headers"],
                 auth_headers: dict = SESSION_DEFAULTS["auth_headers"],
                 timeout: int = SESSION_DEFAULTS["timeout"],
                 retries: int = SESSION_DEFAULTS["retries"],
                 max_redirect: int = SESSION_DEFAULTS["max_redirect"],
                 backoff_factor: float = SESSION_DEFAULTS["backoff_factor"],
                 retry_status_code_list: list[int] = SESSION_DEFAULTS["retry_status_codes"],
                 retry_method_list: list[str] = SESSION_DEFAULTS["retry_methods"],
                 respect_retry_headers: bool = SESSION_DEFAULTS["respect_retry_headers"],
                 base_url: str = SESSION_DEFAULTS["base_url"],
                 tls_verify: bool = SESSION_DEFAULTS["tls_verify"],
                 username: str = SESSION_DEFAULTS["username"],
                 password: str = SESSION_DEFAULTS["password"],
                 auth: Optional[Union[tuple, AuthBase]] = None,
                 max_reauth: int = SESSION_DEFAULTS["max_reauth"],
                 **kwargs: Any
                 ) -> None:
        """
        Initialize the object. All provided parameters will be passed through
        a Pydantic model which performs validation and, if necessary, sets
        default values.

        :param timeout: (int) Request timeout in seconds
        :param retries: (int) Total number of retries before failure
        :param max_redirect: (int) Maximum redirects to follow before failure
        :param backoff_factor: (float) Exponential backoff interval for each retry
        :param retry_status_code_list: (list[int]) Force retry on these status codes
        :param retry_method_list: (list[str]) Allow retries on these HTTP methods
        :param respect_retry_headers: (bool) Whether to respect "Retry-After" header
        :param base_url: (URL) If specified, this will be the base URL for all subsequent requests
        :param tls_verify: (bool) Enable/Disable TLS certificate chain validation
        :param username: (str) If specified with password, use for Basic authentication
        :param password: (str) If specified with username, use for Basic authentication
        :param auth: (tuple | AuthBase) If a username/password tuple or an AuthBase instance
            is provided, set the session auth
        """

        if not hasattr(self, "_session_params"):
            self._session_params = HttpSessionArguments(**locals())

        self.http = sessions.BaseUrlSession(base_url=self.base_url)
        self.http.max_redirects = self.max_redirect

        self.http.verify = self.tls_verify
        if not self.tls_verify:
            disable_warnings()

        # requests handles the redirects, so only apply parameters related to
        # retries with this handler.
        default_retry_strategy = Retry(
            total=self.retries,
            other=0,
            redirect=False,
            backoff_factor=self.backoff_factor,
            status_forcelist=self.retry_status_code_list,
            allowed_methods=self.retry_method_list,
            respect_retry_after_header=self.respect_retry_headers,
            raise_on_status=True
        )

        self.http.timeout = self.timeout

        # Mount http/https to the request session and attach the timeout
        # adapter with defined retry strategy
        self.http.mount("https://", TimeoutHTTPAdapter(timeout=self.timeout,
                                                       max_retries=default_retry_strategy))

        self.http.mount("http://", TimeoutHTTPAdapter(timeout=self.timeout,
                                                      max_retries=default_retry_strategy))

        # Is username/password provided, use basic auth. Otherwise if an auth
        # parameter was passed, initialize the session auth object
        if self.username and self.password:
            self.auth = (self.username, self.password)
        elif self.auth:
            self.http.auth = self.auth
        self.reauth_count = 0

        # Assign the response hooks to the session. This should always be:
        #  0: redirect_header_hook (remove auth headers on redirect)
        #  1-x: custom_hooks
        #  Last: request_exception_hook (raise for status and catch exceptions)
        self.redirect_header_hook = remove_custom_auth_header_on_redirect(
            headers=auth_headers.keys()
        )
        self.request_exception_hook = default_request_exception_hook

        self.max_reauth = 3

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Cleanup - terminate the request session
        self.http.close()

    def update_basic_auth(self):
        """
        Called when the username or password properties are changed after
        instantiation. If both properties are present, update the HTTP session
        object to use Basic authentication using the provided credentials.

        :return: None
        """
        if self.username and self.password:
            my_auth_tuple = (self.username, self.password)
            if isinstance(self.auth, tuple) and self.auth != my_auth_tuple:
                self.auth = my_auth_tuple

    @property
    def timeout(self):
        """
        Currently configured HTTP timeout

        :return: Timeout value from _session_params
        """
        return self._session_params.timeout

    @timeout.setter
    def timeout(self, timeout):
        """
        Change the HTTP request timeout for the current session instance.

        Update each mounted adapter (e.g. http:// and https://) to reflect the
        new setting.

        :param timeout: Timeout in seconds
        :return: None
        """
        validated_field = TimeoutValidator(timeout=timeout)
        self._session_params.timeout = validated_field.timeout
        for mounted_adapter in self.http.adapters:
            self.http.get_adapter(mounted_adapter)\
                .timeout = self._session_params.timeout

    @property
    def retries(self):
        """
        Currently configured HTTP retry count

        :return: Retries value from _session_params
        """
        return self._session_params.retries

    @retries.setter
    def retries(self, retries):
        """
        Change the number of HTTP retries for the current session instance.

        Update each mounted adapter (e.g. http:// and https://) to reflect the
        new setting.

        :param retries: Number of retries
        :return: None
        """
        validated_field = RetriesValidator(retries=retries)
        self._session_params.retries = validated_field.retries
        for mounted_adapter in self.http.adapters:
            self.http.get_adapter(mounted_adapter)\
                .max_retries.total = self._session_params.retries

    @property
    def max_redirect(self):
        """
        Currently configured number of max redirects to follow

        :return: Max redirect value from _session_params
        """
        return self._session_params.max_redirect

    @max_redirect.setter
    def max_redirect(self, max_redirect):
        """
        Change the max number of redirects for the current session instance.

        Update each mounted adapter (e.g. http:// and https://) to reflect the
        new setting.

        :param max_redirect: Max redirects to follow
        :return: None
        """
        validated_field = MaxRedirectValidator(max_redirect=max_redirect)
        self._session_params.max_redirect = validated_field.max_redirect
        # self.http.max_redirects = self._session_params.max_redirect
        for mounted_adapter in self.http.adapters:
            self.http.get_adapter(mounted_adapter)\
                .max_retries.redirect = self._session_params.max_redirect

    @property
    def backoff_factor(self):
        """
        Currently configured backoff factor for retries. From the urllib3
        documentation, backoff factor applies between attempts after the
        *second* try and the sleep will be for:

        {backoff factor} * (2 ** ({number of total retries} - 1)) seconds.

        :return: Backoff factor from _session_params
        """
        return self._session_params.backoff_factor

    @backoff_factor.setter
    def backoff_factor(self, backoff_factor):
        """
        Change the backoff factor for the current session instance.

        Update each mounted adapter (e.g. http:// and https://) to reflect the
        new setting.

        :param backoff_factor: Backoff factor for retries
        :return: None
        """
        validated_field = BackoffFactorValidator(backoff_factor=backoff_factor)
        self._session_params.backoff_factor = validated_field.backoff_factor
        for mounted_adapter in self.http.adapters:
            self.http.get_adapter(mounted_adapter)\
                .max_retries.backoff_factor = self._session_params.backoff_factor

    @property
    def retry_status_code_list(self):
        """
        Currently configured list of status codes that result in a retry

        :return: Status code list from _session_params
        """
        return self._session_params.retry_status_code_list

    @retry_status_code_list.setter
    def retry_status_code_list(self, retry_status_code_list):
        """
        Change the list of status codes that result in a retry when received.

        Update each mounted adapter (e.g. http:// and https://) to reflect the
        new setting.

        :param retry_status_code_list: List of HTTP status codes to retry
        :return: None
        """
        validated_field = RetryStatusCodeListValidator(
            retry_status_code_list=retry_status_code_list
        )
        self._session_params.retry_status_code_list = validated_field.retry_status_code_list
        for mounted_adapter in self.http.adapters:
            self.http.get_adapter(mounted_adapter)\
                .max_retries.status_forcelist = self._session_params.retry_status_code_list

    @property
    def retry_method_list(self):
        """
        Currently configured list of retry methods. When one of the listed is
        executed and the result is in the retry_status_code_list, perform a
        retry.

        :return: Retry method list from _session_params
        """
        return self._session_params.retry_method_list

    @retry_method_list.setter
    def retry_method_list(self, retry_method_list):
        """
        Change the list of HTTP methods that will be retried if a
        retry_status_code_list result is received.

        Update each mounted adapter (e.g. http:// and https://) to reflect the
        new setting.

        :param retry_method_list: List of HTTP methods to retry
        :return: None
        """
        validated_field = RetryMethodListValidator(retry_method_list=retry_method_list)
        self._session_params.retry_method_list = validated_field.retry_method_list
        for mounted_adapter in self.http.adapters:
            self.http.get_adapter(mounted_adapter)\
                .max_retries.allowed_methods = self._session_params.retry_method_list

    @property
    def respect_retry_headers(self):
        """
        Currently configured setting for respecting Retry-After headers when
        received for status codes in the retry_status_code_list

        :return: Boolean from _session_params
        """
        return self._session_params.respect_retry_headers

    @respect_retry_headers.setter
    def respect_retry_headers(self, respect_retry_headers):
        """
        Change the behavior when a response includes Retry-After header for the
        current instance of the session.

        Update each mounted adapter (e.g. http:// and https://) to reflect the
        new setting.

        :param respect_retry_headers: True to respect, False to ignore
        :return: None
        """
        validated_field = RespectRetryHeadersValidator(respect_retry_headers=respect_retry_headers)
        self._session_params.respect_retry_headers = validated_field.respect_retry_headers
        for mounted_adapter in self.http.adapters:
            self.http.get_adapter(mounted_adapter)\
                .max_retries.respect_retry_after_header = self._session_params.respect_retry_headers

    @property
    def base_url(self):
        """
        Currently configured Base URL for the session instance.

        :return: Base URL value from _session_params
        """
        return self._session_params.base_url

    @base_url.setter
    def base_url(self, base_url):
        """
        Change the Base URL for the current session instance. Currently, this
        uses the Request BaseUrlSession interface which implements the urllib3
        "urljoin" method.

        Base URLs should end with a tailing slash (/) and paths relative
        to the Base URL should begin WITHOUT a leading slash, else strange
        outcomes may occur.

        TODO - Add a flag (simple_baseurl?) to handle this automagically

        :param base_url: Base URL for requests using this instance
        :return: None
        """
        validated_field = BaseUrlValidator(base_url=base_url)
        self._session_params.base_url = validated_field.base_url
        self.http.base_url = self._session_params.base_url

    @property
    def tls_verify(self):
        """
        Current configuration of the TLS Certificate Chain Validation parameter

        :return: TLS verification boolean from _session_params
        """
        return self._session_params.tls_verify

    @tls_verify.setter
    def tls_verify(self, tls_verify):
        """
        Change the TLS chain validation setting for the current instance. This
        should only be disabled for dev / testing purposes, never in production

        :param tls_verify: True = perform certificate chain validation.
            Setting this to False disable TLS validation.
        :return: None
        """
        validated_field = TlsVerifyValidator(tls_verify=tls_verify)
        self._session_params.tls_verify = validated_field.tls_verify
        if self._session_params.tls_verify is False:
            disable_warnings()
        self.http.verify = self._session_params.tls_verify

    @property
    def username(self):
        """
        Currently configured username for HTTP Basic Auth

        :return: Username from _session_params.username
        """
        return self._session_params.username

    @username.setter
    def username(self, username):
        """
        Update the username for HTTP Basic auth. Once a username and password
        have both been configured, Basic auth will be configured for the
        session instance.

        :param username: Username for HTTP Basic Auth
        :return: None
        """
        validated_field = UsernameValidator(username=username)
        self._session_params.username = validated_field.username
        self.update_basic_auth()

    @property
    def password(self):
        """
        Currently configured password for HTTP Basic Auth

        :return: Password from _session_params.username
        """
        return self._session_params.password

    @password.setter
    def password(self, password):
        """
        Update the password for HTTP Basic auth. Once configured along with
        a username, Basic auth will be configured for the session instance.

        :param password: Password for HTTP Basic Auth
        :return: None
        """
        validated_field = PasswordValidator(password=password)
        self._session_params.password = validated_field.password
        self.update_basic_auth()

    @property
    def auth(self):
        """
        Currently configured authorization method for the HTTP session

        :return: auth attribute from session object
        """
        return self._session_params.auth

    @auth.setter
    def auth(self, auth_method=None):
        """
        Update the auth method for the HTTP session. This can be used in lieu
        of the username and password attributes, or a custom AuthBase instance
        can be provided if desired.

        Basic auth is provided as a tuple (username, password) and will update
        the object attributes if provided.

        :param auth_method: Authorization method for the HTTP session.
        :return: None
        """
        # pylint: disable=unsubscriptable-object

        validated_field = AuthValidator(auth=auth_method)
        if isinstance(validated_field.auth, tuple):
            self._session_params.username = validated_field.auth[0]
            self._session_params.password = validated_field.auth[1]
        self._session_params.auth = validated_field.auth
        self.http.auth = self._session_params.auth

    @property
    def headers(self):
        """
        Currently configured headers to include in the request.

        :return: headers attribute from session object
        """
        return self._session_params.headers

    @headers.setter
    def headers(self, headers: Optional[dict[str, str]] = MappingProxyType({})):
        """
        Update the HTTP headers for the current session. This should NOT be
        used for authentication headers, as these will not be removed on a
        cross-domain redirect. Use the auth_headers attribute for those.

        :param headers: Dictionary of additional headers for the session.
        :return: None
        """
        self._session_params.headers = headers
        self.http.headers = self._session_params.headers

    @property
    def auth_headers(self):
        """
        Currently configured custom authentication/authorization headers.

        :return: auth headers from the session object
        """
        return self._session_params.auth_headers

    @auth_headers.setter
    def auth_headers(self, headers: Optional[dict[str, str]] = MappingProxyType({})):
        """
        Add custom auth headers (X-Auth-Token, etc) for the request session
        object. The differentiator with auth_headers is that each custom
        auth header provided here will be added to the redirect hook which
        will remove them on a cross-domain redirect.

        :param headers: Dictionary of custom auth headers for the session
        :return: None
        """
        self._session_params.auth_headers = headers
        self.http.headers = self._session_params.auth_headers

        self.redirect_header_hook = remove_custom_auth_header_on_redirect(headers=headers.keys())

    def reauth(self):
        """
        Attempt the last request if a 401 is received. If called, check for
        the reauth attempt number and, if less than the max reauth,
        perform a re-auth for the session and retry the request.

        :return: None
        :raises: RequestHTTPError if max auth count reached
        """
        if hasattr(self.auth, "reauth"):
            if self.reauth_count >= self.max_reauth:
                raise RequestHTTPError(
                    f"Maximum reauthentication count reached ({self.reauth_count})"
                )
            self.reauth_count += 1
            self.auth.reauth()

    @property
    def redirect_header_hook(self):
        """
        Currently configured response hook for redirect handling

        :return: session response hook for redirects
        """
        return self._session_params.redirect_header_hook

    @redirect_header_hook.setter
    def redirect_header_hook(self, hook):
        """
        Set (or replace) the response hook to handle redirects. By default,
        the hook is configured to remove any custom auth headers before
        re-sending a request when a redirect is received.

        This hook will be the FIRST hook executed after a response.

        :param headers: Function reference to become the redirect handler
        :return: None
        """
        if not isinstance(hook, list):
            hook = [hook]
        self._session_params.redirect_header_hook = hook
        self.http.hooks["response"] = self.redirect_header_hook + \
                                      self.response_hooks + \
                                      self.request_exception_hook

    @property
    def request_exception_hook(self):
        """
        Currently configured response hook for exception handling

        :return: session response hook for exceptions
        """
        return self._session_params.request_exception_hook

    @request_exception_hook.setter
    def request_exception_hook(self, hook):
        """
        Set (or replace) the exception hook to handle HTTP errors.

        By default, the hook will re-raise various exceptions generated
        by the requests library or urllib3; however, it may be desirable to
        replace this hook if custom exceptions should be raised.

        This hook will be the LAST hook raised after a response, after the
        redirect hook and any custom hooks.

        :param headers: Function reference to become the exception handler hook
        :return: None
        """
        if not isinstance(hook, list):
            hook = [hook]
        self._session_params.request_exception_hook = hook
        self.http.hooks["response"] = self.redirect_header_hook + \
                                      self.response_hooks + \
                                      self.request_exception_hook

    @property
    def response_hooks(self):
        """
        Currently configured custom response hooks.

        :return: User-defined custom response hooks
        """
        return self._session_params.response_hooks

    @response_hooks.setter
    def response_hooks(self, hooks):
        """
        Add response hook(s) to be executed after a response is received.

        Either a list of hooks can be provided, or a single hook. If a single
        hook is passed, it will be appended to the list of exisiting response
        hooks.

        These response hooks will be executed AFTER the redirect hook and
        BEFORE any exception handler hook.

        :param headers: Function(s) to call after a response is received.
        :return: None
        """
        if not isinstance(hooks, list):
            hooks = [hooks]

        self._session_params.response_hooks = self._session_params.response_hooks + hooks
        self.http.hooks["response"] = self.redirect_header_hook + \
                                      self.response_hooks + \
                                      self.request_exception_hook

    def clear_response_hooks(self):
        """
        Clear all user-defined response hooks.

        :return: None
        """
        self._session_params.response_hooks = []
        self.http.hooks["response"] = []

    def request(self, method, url, **kwargs):
        """
        Send a generic HTTP request. See the Python "requests" library for
        detailed parameters available for any HTTP Request. "Standard" methods
        i.e. GET, POST, etc. are wrappers for this method, which itself is a
        wrapper for the requests library's "request" function.

        :param method: HTTP Method for the request
        :param url: Absolute or relative URL (BaseURL sessions only) for the
            request.
        :param kwargs: Additional parameters to pass to requests.request
        :return: :class:`Response <Response>` object
        """
        if "timeout" in kwargs:
            del kwargs["timeout"]

        return self.http.request(method, url, timeout=self.timeout, **kwargs)

    def get(self, url, params=None, **kwargs):
        """
        Send an HTTP GET request

        :param url: Absolute or relative URL for the request
        :param params: Optional parameters to include in the request string.
        :param kwargs: Optional arguments for requests.request
        :return: :class:`Response <Response>` object
        """
        return self.http.request("get", url, params=params, **kwargs)

    def options(self, url, **kwargs):
        """
        Send an HTTP OPTIONS request

        :param url: Absolute or relative URL for the request
        :param kwargs: Optional arguments for requests.request
        :return: :class:`Response <Response>` object
        """
        return self.http.request("options", url, **kwargs)

    def head(self, url, **kwargs):
        """
        Send an HTTP HEAD request

        :param url: Absolute or relative URL for the request
        :param kwargs: Optional arguments for requests.request
        :return: :class:`Response <Response>` object
        """
        kwargs.setdefault("allow_redirects", False)
        return self.http.request("head", url, **kwargs)

    def post(self, url, data=None, json=None, **kwargs):
        """
        Send an HTTP POST request

        :param url: Absolute or relative URL for the request
        :param data: Raw data (e.g. Dict, list, etc.) to send in the POST body
        :param json: JSON-compatible Python object to serialize for the body
        :param kwargs: Optional arguments for requests.request
        :return: :class:`Response <Response>` object
        """
        return self.http.request("post", url, data=data, json=json, **kwargs)

    def put(self, url, data=None, json=None, **kwargs):
        """
        Send an HTTP PUT request

        :param url: Absolute or relative URL for the request
        :param data: Raw data (e.g. Dict, list, etc.) to send in the POST body
        :param json: JSON-compatible Python object to serialize for the body
        :param kwargs: Optional arguments for requests.request
        :return: :class:`Response <Response>` object
        """
        return self.http.request("put", url, data=data, json=json, **kwargs)

    def patch(self, url, data=None, json=None, **kwargs):
        """
        Send an HTTP PATCH request

        :param url: Absolute or relative URL for the request
        :param data: Raw data (e.g. Dict, list, etc.) to send in the POST body
        :param json: JSON-compatible Python object to serialize for the body
        :param kwargs: Optional arguments for requests.request
        :return: :class:`Response <Response>` object
        """
        return self.http.request("patch", url, data=data, json=json, **kwargs)

    def delete(self, url, **kwargs):
        """
        Send an HTTP DELETE request

        :param url: Absolute or relative URL for the request
        :param kwargs: Optional arguments for requests.request
        :return: :class:`Response <Response>` object
        """
        return self.http.request("delete", url, **kwargs)
