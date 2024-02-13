"""
Default hooks for response handling. These are separated from the main module
to improve readability of it as well as the hook definitions.
"""
import logging
from ssl import SSLError
from requests.exceptions import (HTTPError as RequestHTTPError,
                                 ConnectionError as RequestConnectionError,
                                 InvalidJSONError as RequestInvalidJSONError,
                                 Timeout as RequestTimeout,
                                 MissingSchema as RequestMissingSchema,
                                 RetryError as RequestRetryError,
                                 TooManyRedirects as RequestTooManyRedirects,
                                 SSLError as RequestSslError,
                                 RequestException)
from urllib3.exceptions import (MaxRetryError, SSLError as UrllibSslError)


logger = logging.getLogger(__name__)


def default_request_exception_hook(response, **kwargs):  # pylint: disable=unused-argument
    """
    This function is bound to the HTTP Session object and raises the request
    Response for status, catches exceptions, and re-raises the same exception
    to be handled by the calling script. This avoids having to repeat the
    raise_for_status() method each time a request is made by the caller.

    The response hook can be overridden during or after class instantiation
    to permit app-specific custom exception raises.

    :param response: Requests response object
    :return: None
    """
    try:
        response.raise_for_status()
    except RequestTooManyRedirects as err:
        logger.error("Too many redirects occurred when processing the request: %s", err)
        raise RequestTooManyRedirects(err) from err
    except RequestRetryError as err:
        logger.error("Request retry handler error was encountered: %s", err)
        raise RequestRetryError(err) from err
    except (RequestSslError, SSLError, UrllibSslError, MaxRetryError) as err:
        logger.error("TLS error encountered during request: %s", err)
        raise RequestSslError(err) from err
    except RequestTimeout as err:
        logger.error("The HTTP request timed out: %s", err)
        raise RequestTimeout(err) from err
    except RequestConnectionError as err:
        logger.error("A connection error occurred while processing the request: %s", err)
        raise RequestConnectionError(err) from err
    except RequestHTTPError as err:
        logger.error("Error performing HTTP request: %s", err)
        raise RequestHTTPError(err) from err
    except RequestInvalidJSONError as err:
        logger.error("An error occurred processing JSON for the request: %s", err)
        raise RequestInvalidJSONError(err) from err
    except RequestMissingSchema as err:
        logger.error("Missing scheme in request. "
                     "Check that base_url is set if using relative path: %s", err)
        raise RequestMissingSchema(err) from err
    except RequestException as err:
        logger.error("An unspecified request exception was encountered: %s", err)
        raise RequestException(err) from err

    return response


# def remove_custom_auth_header_on_redirect(headers: Optional[list[str]] = (), *args, **kwargs):
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
#             # Only strip the headers when being redirected to a different host
#             response.request.headers = {
#                 k: v for k, v in response.request.headers.items() if k not in headers
#             }
#         return response
#
#     return redirect_header_hook
