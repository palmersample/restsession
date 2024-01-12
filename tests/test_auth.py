"""
Test functions for request authorization
"""
# Safe to disable missing-timeout because the request session class has a
# default timeout adapter mounted.
# pylint: disable=redefined-outer-name, missing-timeout
# pylint: disable=too-few-public-methods, useless-return, invalid-name, too-many-arguments
import base64
from urllib.parse import urlparse
import json
import logging
from http.server import BaseHTTPRequestHandler
import pytest
import requests
import requests.exceptions
import requests.utils
import requests_toolbelt.sessions
# import restsession
# import restsession.defaults
import restsession.exceptions
from .conftest import BaseHttpServer, MockServerRequestHandler


logger = logging.getLogger(__name__)


pytestmark = pytest.mark.auth

CUSTOM_AUTH_TOKEN_ONE = "super_big_token_thing"
CUSTOM_AUTH_TOKEN_TWO = "this_is_a_second_token"
CUSTOM_AUTH_HEADER = "X-AUTH-TOKEN"


class ExampleTokenAuth(requests.auth.AuthBase):
    """
    Generic custom auth class to simulate obtaining a token via POST and
    including the token into a custom request header.
    """
    auth_request_count = 0
    header_usage_count = 0

    def __init__(self, auth_url, username, password):
        self.__class__.auth_request_count += 1
        self.auth_url = auth_url
        self.username = username
        self.password = password
        if not hasattr(self, "token"):
            logger.info("Calling token POST")
            self.token = self.get_token()
            logger.info("Received token: %s", self.token)
        else:
            logger.info("Token already present")

    def get_token(self):
        """
        Retrieve the token from a mock server using an HTTP POST

        :return: Token retrieved from the mock server
        """
        token_result = requests.post(self.auth_url, auth=(self.username, self.password))
        token = token_result.json()["token"]
        return token

    def __call__(self, r):
        logger.info("Dir of r in __call__: %s", dir(r))
        if hasattr(r, "status_code") and r.status_code == 401:
            logger.error("Status code in __call__ is 401!")
        r.headers[CUSTOM_AUTH_HEADER] = self.token
        logger.info("Headers: %s", r.headers)
        self.__class__.header_usage_count += 1
        r.register_hook("response", self.redirect)
        r.register_hook("response", self.reauth)
        return r

    def reauth(self, r, **kwargs):
        """
        Reauthentication hook - complete and close the connection, get a new
        token, re-prepare the request, and return the reference to the
        prepared request.

        :param r: Response object
        :param kwargs: Keyword arguments from the request session
        :return: Updated prepared request on 401, original request object otherwise
        """
        if r.status_code == 401:
            self.__class__.auth_request_count += 1
            logger.info("Reauthenticating...")
            logger.info("Details: URL %s, auth %s %s",
                        self.auth_url,
                        self.username,
                        self.password)
            r.content  # pylint: disable=pointless-statement
            r.close()
            prep = r.request.copy()
            logger.debug("Pre-reauth Prep headers:\n%s", prep.headers)
            prep.headers[CUSTOM_AUTH_HEADER] = self.get_token()
            logger.debug("Prep headers:\n%s", prep.headers)
            _r = r.connection.send(prep, **kwargs)
            _r.history.append(r)
            _r.request = prep
            logger.error(prep)
            return _r

        return r

    def redirect(self, r, **kwargs):  # pylint: disable=unused-argument
        """
        Redirect hook. Remove any authorization headers for this request on a
        different origin redirect.

        :param r: Response object
        :param kwargs: Keyword arguments
        :return: Updated response object without the custom auth header
        """
        if r.is_redirect and \
                (urlparse(r.request.url).netloc !=
                 urlparse(r.headers["Location"]).netloc):
            logger.info("Redirect to different origin...")
            r.request.headers = {
                k: v for k, v in r.request.headers.items() if k != CUSTOM_AUTH_HEADER
            }
        return r


class AuthMockServerRequestHandler(BaseHTTPRequestHandler):
    """
    Authentication mock server. If a POST request is received, return a token.

    If a subsequent POST is received, return a potentially different token.

    Use for testing requests custom auth classes.
    """
    server_address = None
    request_count = 0
    auth_token_one = "token_one"
    auth_token_two = "token_two"

    def do_POST(self):
        """
        HTTP POST handler. Return a token to the caller, regardless of whether
        the POST includes any authorization headers.

        :return: None
        """
        logger.debug("Received POST request to Auth Mock Server")
        self.send_response(200)
        self.send_header(
            "Content-Type", "application/json; charset=utf-8"
        )
        self.end_headers()
        if self.__class__.request_count == 0:
            logger.debug("Auth mock server: sending token one (request %s)",
                         self.__class__.request_count)
            self.wfile.write(bytes(json.dumps({"token": self.__class__.auth_token_one}), "utf-8"))
            self.__class__.request_count += 1
        else:
            logger.debug("Auth mock server: sending token two (request %s)",
                         self.__class__.request_count)
            self.wfile.write(bytes(json.dumps({"token": self.__class__.auth_token_two}), "utf-8"))
            self.__class__.request_count = 0
        return


class UnauthorizedMockServerRequestHandler(MockServerRequestHandler):
    """
    The target handler - once auth is performed, this is the class to
    process authorized requests. Inherits from the generic Mock Server
    handler so core HTTP methods will return the default_response
    """
    max_retry = 1
    request_count = 0

    def send_default_response(self):
        """
        Generic response for tests in this file. Return any received headers
        and body content as a JSON-encoded dictionary with key "headers"
        containing received headers and key "body" with received body.

        :return: None
        """
        logger.debug("Received request")
        logger.debug("UnauthorizedMockServerRequestHandler headers: %s", self.headers)
        if self.__class__.request_count < self.__class__.max_retry:
            self.send_response(401)
            self.__class__.request_count += 1
        else:
            self.send_response(200)
        self.send_header(
            "Content-Type", "application/json; charset=utf-8"
        )
        self.end_headers()
        response_data = {
            "headers": dict(self.headers),
            "body": {}
        }
        self.wfile.write(bytes(json.dumps(response_data).encode("utf-8")))


@pytest.fixture(scope="module")
def auth_mock_server():
    """
    Fixture for the generic HTTP mock server defined below. Use for
    non-specific tests to verify core functionality.

    :return: Instance of BaseHttpServer with the redirect handler.
    """
    return BaseHttpServer(handler=AuthMockServerRequestHandler)


@pytest.fixture(scope="function", autouse=True)
def reset_auth_mock_server():
    """
    Reset the authorization mock server class variables after each function

    :return: None
    """
    AuthMockServerRequestHandler.request_count = 0
    AuthMockServerRequestHandler.auth_token_one = CUSTOM_AUTH_TOKEN_ONE
    AuthMockServerRequestHandler.auth_token_two = CUSTOM_AUTH_TOKEN_TWO


@pytest.fixture(scope="module")
def unauthorized_mock_server():
    """
    Fixture for the generic HTTP mock server defined below. Use for
    non-specific tests to verify core functionality.

    :return: Instance of BaseHttpServer with the unauthorized handler.
    """
    return BaseHttpServer(handler=UnauthorizedMockServerRequestHandler)


@pytest.fixture(scope="function", autouse=True)
def reset_unauthorized_mock_server():
    """
    Reset the unauthorized mock server class variables after each function

    :return: None
    """
    UnauthorizedMockServerRequestHandler.request_count = 0
    UnauthorizedMockServerRequestHandler.max_retry = 1


@pytest.fixture
def custom_auth_class():
    """
    Fixture for the custom requests.auth.AuthBase class

    :return: Custom auth class for request testing
    """
    ExampleTokenAuth.auth_request_count = 0
    ExampleTokenAuth.header_usage_count = 0
    return ExampleTokenAuth


@pytest.fixture
def custom_auth_token_one():
    """
    Generic authorization token for tests

    :return: String value to be used for test comparison
    """
    return CUSTOM_AUTH_TOKEN_ONE


@pytest.fixture
def custom_auth_token_two():
    """
    Alternate generic authorization token for tests

    :return: String value to be used for test comparison
    """
    return CUSTOM_AUTH_TOKEN_TWO


@pytest.fixture
def custom_auth_header():
    """
    Generic authorization header key to send for tests

    :return: String value to be used as a generic auth header key
    """
    return CUSTOM_AUTH_HEADER


def test_basic_auth(test_class,
                    request_method,
                    generic_mock_server):
    """
    Test basic authorization

    :param test_class: Fixture of the class to test
    :param request_method: Fixture of the HTTP verb to test
    :param generic_mock_server: Fixture for the generic mock server
    :return: None
    """
    with test_class() as class_instance:
        auth_user = "username"
        auth_pass = "password"
        class_instance.auth = (auth_user, auth_pass)
        logger.error("TEST - INSTALLED HOOKS: %s", class_instance.hooks)
        authorization_string = f"{auth_user}:{auth_pass}"
        base64_auth = base64.b64encode(bytes(authorization_string, 'utf-8')).decode('utf-8')
        expected_auth_value = f"Basic {base64_auth}"
        response = class_instance.request(request_method, generic_mock_server.url)
        received_headers = response.json().get("headers")
        logger.error("Received AUTH headers: %s",
                     received_headers)
        logger.info("Desired: %s , Received: %s",
                    expected_auth_value,
                    received_headers.get("Authorization"))
        assert received_headers.get("Authorization") == expected_auth_value


@pytest.mark.custom_auth
def test_custom_auth_class(test_class,
                           request_method,
                           custom_auth_header,
                           custom_auth_token_one,
                           generic_mock_server,
                           custom_auth_class,
                           auth_mock_server):
    """
    Test a custom authorization class. The request should get a token via POST
    to a mock server, then use that token for a request to a different mock
    server.

    :param test_class: Fixture of the class to test
    :param request_method: Fixture of the HTTP verb to test
    :param custom_auth_token_one: Fixture for a generic token string
    :param generic_mock_server: Fixture for the generic mock server
    :return: None
    """
    with test_class() as class_instance:
        auth_server = auth_mock_server
        auth_server.mock_server.RequestHandlerClass.auth_token_one = custom_auth_token_one
        auth_server.mock_server.RequestHandlerClass.auth_token_two = custom_auth_token_two
        class_instance.auth = custom_auth_class(auth_url=auth_server.url,
                                                username="username",
                                                password="password")

        auth_response = class_instance.request(request_method, generic_mock_server.url)
        received_headers = auth_response.json().get("headers")
        assert received_headers.get(custom_auth_header, "") == custom_auth_token_one


@pytest.mark.custom_auth
def test_custom_auth_retry_on_failure(test_class,
                                      request_method,
                                      custom_auth_header,
                                      custom_auth_token_two,
                                      auth_mock_server,
                                      custom_auth_class,
                                      unauthorized_mock_server):
    """
    If authorization fail is received, test that the custom auth class with
    attempt to reauthenticate and resend the request.

    :param test_class: Fixture of the class to test
    :param request_method: Fixture of the HTTP verb to test
    :param custom_auth_header: Fixture for the custom auth header key
    :param custom_auth_token_one: Fixture for a generic token string
    :param custom_auth_token_two: Second fixture for generic token string
    :return: None
    """
    with test_class() as class_instance:
        auth_server = auth_mock_server
        target_server = unauthorized_mock_server
        class_instance.auth = custom_auth_class(auth_url=auth_server.url,
                                                username="username",
                                                password="password")

        logger.error("Class instance hooks NOW: %s", class_instance.hooks)
        auth_response = class_instance.request(request_method, target_server.url)
        received_headers = auth_response.json().get("headers")

        # The first request resulted in a 401, so a reauth should happen and the
        # X-Auth-Token should be for token two.
        assert received_headers.get(custom_auth_header) == custom_auth_token_two


@pytest.mark.basic_auth
def test_basic_auth_header_removed_on_redirect(test_class,
                                               request_method,
                                               generic_mock_server,
                                               redirect_mock_server):
    """
    Test the Authorization: Basic header is removed on a different-origin
    redirect.

    :param test_class: Fixture of the class to test
    :param request_method: Fixture of the HTTP verb to test
    :param generic_mock_server: Fixture for the generic mock server
    :return: None
    """
    with test_class() as class_instance:
        auth_server = redirect_mock_server
        auth_server.set_handler_redirect(next_server=generic_mock_server.url, max_redirect=1)
        logger.error("Redirect next server: %s",
                     redirect_mock_server.mock_server.RequestHandlerClass.next_server)

        logger.error("Auth server URL: %s", redirect_mock_server.url)
        logger.error("Target server URL: %s", generic_mock_server.url)
        # FirstMockServerRequestHandler.next_server = generic_mock_server.url

        auth_user = "username"
        auth_pass = "password"
        class_instance.auth = (auth_user, auth_pass)

        auth_response = class_instance.request(request_method, redirect_mock_server.url)
        received_headers = auth_response.json().get("headers")
        logger.debug("Test class received response headers:\n%s", received_headers)

        # The first request resulted in a redirect, Authorization should be removed
        assert "Authorization" not in received_headers, \
            "Authorization header was returned by the second server"


def test_custom_auth_header_removed_on_redirect(test_class,
                                                request_method,
                                                generic_mock_server,
                                                redirect_mock_server,
                                                custom_auth_header,
                                                custom_auth_token_one):
    """
    Test that a custom authorization header is removed on different-origin
    redirects

    :param test_class: Fixture of the class to test
    :param request_method: Fixture of the HTTP verb to test
    :param generic_mock_server: Fixture for the generic mock server
    :param redirect_mock_server: Fixture for the redirect mock server
    :param custom_auth_header: Fixture for custom auth header name
    :param custom_auth_token_one: Fixture for the first custom auth token
    :return: None
    """

    with test_class() as class_instance:
        auth_server = redirect_mock_server
        target_server = generic_mock_server
        auth_server.set_handler_redirect(next_server=target_server.url, max_redirect=1)

        class_instance.auth_headers = {custom_auth_header: custom_auth_token_one}

        auth_response = class_instance.request(request_method, auth_server.url)
        received_headers = auth_response.json().get("headers")
        logger.debug("Test class received response headers:\n%s", received_headers)

        # The first request resulted in a redirect, Authorization should be removed
        assert custom_auth_header not in received_headers, \
            f"Header '{custom_auth_header}' was returned by the second server"


@pytest.mark.redirect_auth
def test_custom_auth_class_removed_on_redirect(test_class,
                                               request_method,
                                               generic_mock_server,
                                               auth_mock_server,
                                               redirect_mock_server,
                                               custom_auth_class,
                                               custom_auth_header):
    """

    :param test_class: Fixture of the class to test
    :param request_method: Fixture of the HTTP verb to test
    :param generic_mock_server: Fixture for the generic mock server
    :param auth_mock_server: Fixture for the authentication mock server
    :param redirect_mock_server: Fixture for the redirect mock server
    :param custom_auth_class: Fixture for the custom requests auth class
    :param custom_auth_header: Fixture for custom auth header name
    :return: None
    """
    with test_class() as class_instance:
        auth_server = auth_mock_server
        class_instance.auth = custom_auth_class(auth_url=auth_server.url,
                                                username="username",
                                                password="password")
        first_server = redirect_mock_server
        target_server = generic_mock_server
        first_server.set_handler_redirect(next_server=target_server.url, max_redirect=1)

        auth_response = class_instance.request(request_method, first_server.url)
        received_headers = auth_response.json().get("headers")
        logger.info("RECEIVED final: %s", received_headers)

        # The first request resulted in a 401, so a reauth should happen and the
        # X-Auth-Token should be for token two.
        assert custom_auth_header not in received_headers, \
            "Custom auth header still present in response"


@pytest.mark.basic_auth
def test_basic_auth_header_not_removed_on_same_origin_redirect(test_class,
                                                               request_method,
                                                               redirect_mock_server):
    """
    Test that the basic auth header is returned on a same-origin redirect.

    :param test_class: Fixture of the class to test
    :param request_method: Fixture of the HTTP verb to test
    :param redirect_mock_server: Fixture for the redirect mock server
    :return: None
    """

    with test_class() as class_instance:
        target_server = redirect_mock_server
        target_server.set_handler_redirect(next_server=target_server.url, max_redirect=1)

        auth_user = "username"
        auth_pass = "password"
        class_instance.auth = (auth_user, auth_pass)
        authorization_string = f"{auth_user}:{auth_pass}"
        base64_auth = base64.b64encode(bytes(authorization_string, 'utf-8')).decode('utf-8')
        expected_auth_value = f"Basic {base64_auth}"

        auth_response = class_instance.request(request_method, target_server.url)
        received_headers = auth_response.json().get("headers")
        logger.debug("Test class received response headers:\n%s", received_headers)

        # The first request resulted in a redirect, Authorization should be removed
        assert received_headers.get("Authorization", "") == expected_auth_value, \
            "Expected auth value NOT preserved on same-origin redirect."


@pytest.mark.parametrize("test_class",
                         [
                             pytest.param(requests_toolbelt.sessions.BaseUrlSession,
                                          marks=pytest.mark.xfail(
                                              reason="Requests does not have auth_headers attribute")
                                          ),
                             restsession.RestSession,
                             restsession.RestSessionSingleton
                         ])
def test_custom_auth_header_not_removed_on_same_origin_redirect(test_class,
                                                                request_method,
                                                                redirect_mock_server,
                                                                custom_auth_header,
                                                                custom_auth_token_one):
    """
    Test that a custom auth header is returned on a same-origin redirect.

    :param test_class: Fixture of the class to test
    :param request_method: Fixture of the HTTP verb to test
    :param redirect_mock_server: Fixture for the redirect mock server
    :param custom_auth_header: Fixture for custom auth header name
    :param custom_auth_token_one: Fixture for the first custom auth token
    :return: None
    """

    with test_class() as class_instance:
        target_server = redirect_mock_server
        target_server.set_handler_redirect(next_server=target_server.url, max_redirect=1)

        class_instance.auth_headers = {custom_auth_header: custom_auth_token_one}
        auth_response = class_instance.request(request_method, target_server.url)
        received_headers = auth_response.json().get("headers")
        logger.debug("Test class received response headers:\n%s", received_headers)

        # The first request resulted in a redirect, Authorization should be removed
        assert received_headers.get(custom_auth_header, "") == custom_auth_token_one, \
            "Custom auth header NOT preserved on same-origin redirect."


@pytest.mark.redirect_auth
def test_custom_auth_class_not_removed_on_same_origin_redirect(test_class,
                                                               request_method,
                                                               auth_mock_server,
                                                               redirect_mock_server,
                                                               custom_auth_header,
                                                               custom_auth_class,
                                                               custom_auth_token_one):
    """

    :param test_class: Fixture of the class to test
    :param request_method: Fixture of the HTTP verb to test
    :param auth_mock_server: Fixture for the authentication mock server
    :param redirect_mock_server: Fixture for the redirect mock server
    :param custom_auth_header: Fixture for custom auth header name
    :param custom_auth_class: Fixture for the custom requests auth class
    :param custom_auth_token_one: Fixture for the first custom auth token
    :return: None
    """
    with test_class() as class_instance:
        auth_server = auth_mock_server
        class_instance.auth = custom_auth_class(auth_url=auth_server.url,
                                                username="username",
                                                password="password")

        target_server = redirect_mock_server
        target_server.set_handler_redirect(next_server=target_server.url, max_redirect=1)

        auth_response = class_instance.request(request_method, target_server.url)
        received_headers = auth_response.json().get("headers")
        logger.info("RECEIVED final: %s", received_headers)

        # The first request resulted in a 401, so a reauth should happen and the
        # X-Auth-Token should be for token two.
        assert received_headers.get(custom_auth_header, "") == custom_auth_token_one, \
            "Custom auth header not present in response"
