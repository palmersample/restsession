"""
Test functions for request authorization
"""
# Safe to disable missing-timeout because the request session class has a
# default timeout adapter mounted.
# pylint: disable=redefined-outer-name, missing-timeout, too-few-public-methods, useless-return, invalid-name
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


@pytest.fixture
def custom_auth_token_one():
    """
    Generic authorization token for tests

    :return: String value to be used for test comparison
    """
    return "super_big_token_thing"


@pytest.fixture
def custom_auth_token_two():
    """
    Alternate generic authorization token for tests

    :return: String value to be used for test comparison
    """
    return "this_is_a_second_token"


@pytest.fixture
def custom_auth_header():
    """
    Generic authorization header key to send for tests

    :return: String value to be used as a generic auth header key
    """
    return "X-AUTH-TOKEN"


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


def test_custom_auth_class(test_class,
                           request_method,
                           custom_auth_token_one,
                           generic_mock_server):
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
    class AuthMockServerRequestHandler(MockServerRequestHandler):
        """
        Mock server to handle the authorization POST request.
        """
        server_address = None
        request_count = 0
        received_auth = None

        def do_POST(self):
            self.send_response(200)
            self.send_header(
                "Content-Type", "application/json; charset=utf-8"
            )
            self.end_headers()
            self.wfile.write(bytes(json.dumps({"token": custom_auth_token_one}), "utf-8"))
            return

    class ExampleTokenAuth(requests.auth.AuthBase):
        """
        Custom authorization class that should retrieve a token via POST
        and insert the header into the request.
        """
        auth_request_count = 0
        header_usage_count = 0

        def __init__(self, auth_url, username, password):
            self.__class__.auth_request_count += 1
            if not hasattr(self, "token"):
                logger.info("Calling token POST")
                token_result = requests.post(auth_url, auth=(username, password))
                self.token = token_result.json()["token"]
            else:
                logger.info("Token already present")

        def __call__(self, r):
            r.headers["X-Auth-Token"] = self.token
            self.__class__.header_usage_count += 1
            return r

    with test_class() as class_instance:
        auth_server = BaseHttpServer(handler=AuthMockServerRequestHandler)
        class_instance.auth = ExampleTokenAuth(auth_url=auth_server.url,
                                               username="username",
                                               password="password")
        auth_response = class_instance.request(request_method, generic_mock_server.url)
        received_headers = auth_response.json().get("headers")
        auth_server.stop_server()
        assert received_headers.get("X-Auth-Token") == custom_auth_token_one


def test_custom_auth_retry_on_failure(test_class,
                                      request_method,
                                      custom_auth_header,
                                      custom_auth_token_one,
                                      custom_auth_token_two):
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
    class AuthMockServerRequestHandler(BaseHTTPRequestHandler):
        """
        Mock handler to return a token when a POST is received
        """
        server_address = None
        request_count = 0
        received_auth = None

        def do_POST(self):
            """
            Handle incoming POST request and return a generic token.

            :return: None
            """
            self.send_response(200)
            self.send_header(
                "Content-Type", "application/json; charset=utf-8"
            )
            self.end_headers()
            if self.__class__.request_count == 0:
                logger.info("First auth request - sending custom token one")
                self.wfile.write(bytes(json.dumps({"token": custom_auth_token_one}), "utf-8"))
            else:
                logger.info("Second auth request - sending custom token two")
                self.wfile.write(bytes(json.dumps({"token": custom_auth_token_two}), "utf-8"))
            self.__class__.request_count += 1
            return

    class ExampleTokenAuth(requests.auth.AuthBase):
        """
        Custom auth class to perform a POST and grab a token to insert into
        the request header.
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
            else:
                logger.info("Token already present")

        def get_token(self):
            """
            Minimal function to get a new token from the auth server via HTTP
            POST. TEST/EXAMPLE USE ONLY - NOT FOR PRODUCTION :)

            :return: Token returned by the server
            """
            token_result = requests.post(self.auth_url, auth=(self.username, self.password))
            token = token_result.json()["token"]
            return token

        def __call__(self, r):
            logger.info("Dir of r in __call__: %s", dir(r))
            if hasattr(r, "status_code") and r.status_code == 401:
                logger.error("Status code in __call__ is 401!")
            r.headers[custom_auth_header] = self.token
            self.__class__.header_usage_count += 1
            r.register_hook("response", self.reauth)
            return r

        def reauth(self, r, **kwargs):
            """
            Reauth hook to be called when a new token is required.

            :param r: Requests 'respose' object
            :param kwargs: keyword args passed from the hook
            :return: Modifier response object to be reperformed after reauth
            """
            if r.status_code == 401:
                self.__class__.auth_request_count += 1
                logger.info("Reauthenticating...")
                logger.info("Details: URL %s, auth %s %s",
                            self.auth_url,
                            self.username,
                            self.password)
                # Consume the request content so the connection can be closed.
                r.content  # pylint: disable=pointless-statement
                r.close()
                prep = r.request.copy()
                logger.debug("Pre-reauth Prep headers:\n%s", prep.headers)
                prep.headers[custom_auth_header] = self.get_token()
                logger.debug("Prep headers:\n%s", prep.headers)
                _r = r.connection.send(prep, **kwargs)
                _r.history.append(r)
                _r.request = prep
                logger.error(prep)
                return _r

            return r

    class TargetMockServerRequestHandler(MockServerRequestHandler):
        """
        The target handler - once auth is performed, this is the class to
        process authorized requests. Inherits from the generic Mock Server
        handler so core HTTP methods will return the default_response
        """
        request_count = 0
        def send_default_response(self):
            """
            Generic response for tests in this file. Return any received headers
            and body content as a JSON-encoded dictionary with key "headers"
            containing received headers and key "body" with received body.

            :return: None
            """
            logger.debug("Received request")
            logger.debug("MockServerRequestHandler headers: %s", self.headers)
            self.__class__.request_count += 1
            if self.__class__.request_count == 1:
                self.send_response(401)
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
            return

    with test_class() as class_instance:
        auth_server = BaseHttpServer(handler=AuthMockServerRequestHandler)
        target_server = BaseHttpServer(handler=TargetMockServerRequestHandler)
        class_instance.auth = ExampleTokenAuth(auth_url=auth_server.url,
                                               username="username",
                                               password="password")

        logger.error("Class instance hooks NOW: %s", class_instance.hooks)
        auth_response = class_instance.request(request_method, target_server.url)
        received_headers = auth_response.json().get("headers")
        auth_server.stop_server()
        target_server.stop_server()

        # The first request resulted in a 401, so a reauth should happen and the
        # X-Auth-Token should be for token two.
        assert received_headers.get(custom_auth_header) == custom_auth_token_two


@pytest.mark.basic_auth
def test_basic_auth_header_removed_on_redirect(test_class,
                                               request_method,
                                               generic_mock_server):
    """
    Test the Authorization: Basic header is removed on a different-origin
    redirect.

    :param test_class: Fixture of the class to test
    :param request_method: Fixture of the HTTP verb to test
    :param generic_mock_server:
    :return: None
    """
    class FirstMockServerRequestHandler(MockServerRequestHandler):
        def send_default_response(self):
            """
            Generic response for tests in this file. Return any received headers
            and body content as a JSON-encoded dictionary with key "headers"
            containing received headers and key "body" with received body.

            :return: None
            """
            logger.debug("Received request")
            logger.debug("First server headers: %s", self.headers)
            self.send_response(301)
            self.send_header(
                "Content-Type", "application/json; charset=utf-8"
            )
            logger.debug("Redirecting to %s", self.__class__.next_server)
            self.send_header("Location", self.__class__.next_server)
            self.end_headers()

    with test_class() as class_instance:
        auth_server = BaseHttpServer(handler=FirstMockServerRequestHandler)
        FirstMockServerRequestHandler.next_server = generic_mock_server.url

        auth_user = "username"
        auth_pass = "password"
        class_instance.auth = (auth_user, auth_pass)

        auth_response = class_instance.request(request_method, auth_server.url)
        received_headers = auth_response.json().get("headers")
        logger.debug("Test class received response headers:\n%s", received_headers)
        auth_server.stop_server()
        generic_mock_server.stop_server()

        # The first request resulted in a redirect, Authorization should be removed
        assert "Authorization" not in received_headers, \
            "Authorization header was returned by the second server"


def test_custom_auth_header_removed_on_redirect(test_class,
                                                request_method,
                                                generic_mock_server,
                                                custom_auth_header,
                                                custom_auth_token_one):
    class FirstMockServerRequestHandler(MockServerRequestHandler):
        def send_default_response(self):
            """
            Generic response for tests in this file. Return any received headers
            and body content as a JSON-encoded dictionary with key "headers"
            containing received headers and key "body" with received body.

            :return: None
            """
            logger.debug("Received request")
            logger.debug("First server headers: %s", self.headers)
            self.send_response(301)
            self.send_header(
                "Content-Type", "application/json; charset=utf-8"
            )
            logger.debug("Redirecting to %s", self.__class__.next_server)
            self.send_header("Location", self.__class__.next_server)
            self.end_headers()
            response_data = {
                "headers": dict(self.headers),
                "body": {}
            }
            self.wfile.write(bytes(json.dumps(response_data).encode("utf-8")))

    class TargetMockServerRequestHandler(MockServerRequestHandler):
        ...

    with test_class() as class_instance:
        auth_server = BaseHttpServer(handler=FirstMockServerRequestHandler)
        target_server = BaseHttpServer(handler=TargetMockServerRequestHandler)
        FirstMockServerRequestHandler.next_server = target_server.url

        # auth_user = "username"
        # auth_pass = "password"
        # class_instance.auth = (auth_user, auth_pass)
        class_instance.auth_headers = {custom_auth_header: custom_auth_token_one}

        auth_response = class_instance.request(request_method, auth_server.url)
        received_headers = auth_response.json().get("headers")
        logger.debug("Test class received response headers:\n%s", received_headers)
        auth_server.stop_server()
        target_server.stop_server()

        # The first request resulted in a redirect, Authorization should be removed
        assert custom_auth_header not in received_headers, \
            f"Header '{custom_auth_header}' was returned by the second server"


@pytest.mark.redirect_auth
def test_custom_auth_class_removed_on_redirect(test_class,
                                               request_method,
                                               custom_auth_header,
                                               custom_auth_token_one,
                                               custom_auth_token_two):
    class AuthMockServerRequestHandler(BaseHTTPRequestHandler):
        server_address = None
        request_count = 0
        received_auth = None

        def do_POST(self):
            logger.debug("Received POST request to Auth Mock Server")
            self.send_response(200)
            self.send_header(
                "Content-Type", "application/json; charset=utf-8"
            )
            self.end_headers()
            if self.__class__.request_count == 0:
                self.wfile.write(bytes(json.dumps({"token": custom_auth_token_one}), "utf-8"))
            else:
                self.wfile.write(bytes(json.dumps({"token": custom_auth_token_two}), "utf-8"))
            self.__class__.request_count += 1
            return


    class FirstMockServerRequestHandler(MockServerRequestHandler):
        def send_default_response(self):
            """
            Generic response for tests in this file. Return any received headers
            and body content as a JSON-encoded dictionary with key "headers"
            containing received headers and key "body" with received body.

            :return: None
            """
            logger.debug("Received request")
            logger.debug("First server headers: %s", self.headers)
            self.send_response(301)
            self.send_header(
                "Content-Type", "application/json; charset=utf-8"
            )
            logger.debug("Redirecting to %s", self.__class__.next_server)
            self.send_header("Location", self.__class__.next_server)
            self.end_headers()
            response_data = {
                "headers": dict(self.headers),
                "body": {}
            }
            self.wfile.write(bytes(json.dumps(response_data).encode("utf-8")))

    class TargetMockServerRequestHandler(MockServerRequestHandler):
        ...

    # class ExampleTokenAuth(requests.auth.AuthBase):
    #     auth_request_count = 0
    #     header_usage_count = 0
    #
    #     def __init__(self, auth_url, username, password):
    #         self.__class__.auth_request_count += 1
    #         if not hasattr(self, "token"):
    #             logger.info("Calling token POST")
    #             token_result = requests.post(auth_url, auth=(username, password))
    #             self.token = token_result.json()["token"]
    #         else:
    #             logger.info("Token already present")
    #
    #     def __call__(self, r):
    #         r.headers[custom_auth_header] = self.token
    #         self.__class__.header_usage_count += 1
    #         return r
    #
    #     def reauth(self):
    #         self.__class__.auth_request_count += 1
    #         token_result = requests.get(self.auth_url, auth=(self.username, self.password))
    #         self.token = token_result.json()["token"]

    class ExampleTokenAuth(requests.auth.AuthBase):
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
            else:
                logger.info("Token already present")

        def get_token(self):
            token_result = requests.post(self.auth_url, auth=(self.username, self.password))
            token = token_result.json()["token"]
            return token

        def __call__(self, r):
            logger.info("Dir of r in __call__: %s", dir(r))
            if hasattr(r, "status_code") and r.status_code == 401:
                logger.error("Status code in __call__ is 401!")
            r.headers[custom_auth_header] = self.token
            self.__class__.header_usage_count += 1
            r.register_hook("response", self.redirect)
            r.register_hook("response", self.reauth)
            return r

        def reauth(self, r, **kwargs):
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
                prep.headers[custom_auth_header] = self.get_token()
                logger.debug("Prep headers:\n%s", prep.headers)
                _r = r.connection.send(prep, **kwargs)
                _r.history.append(r)
                _r.request = prep
                logger.error(prep)
                return _r

            return r

        def redirect(self, r, **kwargs):  # pylint: disable=unused-argument
            if r.is_redirect and \
                    (urlparse(r.request.url).netloc !=
                     urlparse(r.headers["Location"]).netloc):
                logger.info("Redirect to different origin...")
                r.request.headers = {
                    k: v for k, v in r.request.headers.items() if k != custom_auth_header
                }
            return r

    with test_class() as class_instance:
        # def auth_response_hook(response, **kwargs):  # pylint: disable=unused-argument
        #     logger.info("Entering auth response hook...")
        #     if response.is_redirect and \
        #             (urlparse(response.request.url).netloc !=
        #              urlparse(response.headers["Location"]).netloc):
        #         logger.info("Auth response hook - deleting auth header.")
        #         logger.info("Response headers: %s", response.headers)
        #         response.request.headers = {
        #             k: v for k, v in response.request.headers.items() if k != custom_auth_header
        #         }
        #
        #         return response

        auth_server = BaseHttpServer(handler=AuthMockServerRequestHandler)
        class_instance.auth = ExampleTokenAuth(auth_url=auth_server.url,
                                               username="username",
                                               password="password")
        # class_instance.response_hooks = auth_response_hook
        first_server = BaseHttpServer(handler=FirstMockServerRequestHandler)
        target_server = BaseHttpServer(handler=TargetMockServerRequestHandler)
        FirstMockServerRequestHandler.next_server = target_server.url

        auth_response = class_instance.request(request_method, first_server.url)
        received_headers = auth_response.json().get("headers")
        logger.info("RECEIVED final: %s", received_headers)
        auth_server.stop_server()
        first_server.stop_server()
        target_server.stop_server()

        # The first request resulted in a 401, so a reauth should happen and the
        # X-Auth-Token should be for token two.
        assert custom_auth_header not in received_headers, \
            "Custom auth header still present in response"


@pytest.mark.basic_auth
def test_basic_auth_header_not_removed_on_same_origin_redirect(test_class,
                                                               request_method,
                                                               generic_mock_server):
    class TargetMockServerRequestHandler(MockServerRequestHandler):
        request_count = 0
        next_server = None

        def send_default_response(self):
            """
            Generic response for tests in this file. Return any received headers
            and body content as a JSON-encoded dictionary with key "headers"
            containing received headers and key "body" with received body.

            :return: None
            """
            if self.__class__.request_count == 0:
                self.__class__.request_count += 1
                logger.debug("Received request")
                logger.debug("First server headers: %s", self.headers)
                self.send_response(301)
                self.send_header(
                    "Content-Type", "application/json; charset=utf-8"
                )
                logger.debug("Redirecting to %s", self.__class__.next_server)
                self.send_header("Location", self.__class__.next_server)
                self.end_headers()
                response_data = {
                    "headers": dict(self.headers),
                    "body": {}
                }
                self.wfile.write(bytes(json.dumps(response_data).encode("utf-8")))
            else:
                logger.debug("Received request")
                logger.debug("Second server headers: %s", self.headers)
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

    with test_class() as class_instance:
        target_server = BaseHttpServer(handler=TargetMockServerRequestHandler)
        TargetMockServerRequestHandler.next_server = target_server.url

        auth_user = "username"
        auth_pass = "password"
        class_instance.auth = (auth_user, auth_pass)
        authorization_string = f"{auth_user}:{auth_pass}"
        base64_auth = base64.b64encode(bytes(authorization_string, 'utf-8')).decode('utf-8')
        expected_auth_value = f"Basic {base64_auth}"

        auth_response = class_instance.request(request_method, target_server.url)
        received_headers = auth_response.json().get("headers")
        logger.debug("Test class received response headers:\n%s", received_headers)
        target_server.stop_server()

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
                                                                custom_auth_header,
                                                                custom_auth_token_one):
    class TargetMockServerRequestHandler(MockServerRequestHandler):
        request_count = 0
        next_server = None

        def send_default_response(self):
            """
            Generic response for tests in this file. Return any received headers
            and body content as a JSON-encoded dictionary with key "headers"
            containing received headers and key "body" with received body.

            :return: None
            """
            if self.__class__.request_count == 0:
                self.__class__.request_count += 1
                logger.debug("Received request")
                logger.debug("First server headers: %s", self.headers)
                self.send_response(301)
                self.send_header(
                    "Content-Type", "application/json; charset=utf-8"
                )
                logger.debug("Redirecting to %s", self.__class__.next_server)
                self.send_header("Location", self.__class__.next_server)
                self.end_headers()
                response_data = {
                    "headers": dict(self.headers),
                    "body": {}
                }
                self.wfile.write(bytes(json.dumps(response_data).encode("utf-8")))
            else:
                logger.debug("Received request")
                logger.debug("Second server headers: %s", self.headers)
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

    logger.error("REQUEST METHOD: %s", request_method)
    with test_class() as class_instance:
        target_server = BaseHttpServer(handler=TargetMockServerRequestHandler)
        TargetMockServerRequestHandler.next_server = target_server.url

        class_instance.auth_headers = {custom_auth_header: custom_auth_token_one}
        auth_response = class_instance.request(request_method, target_server.url)
        received_headers = auth_response.json().get("headers")
        logger.debug("Test class received response headers:\n%s", received_headers)
        target_server.stop_server()

        # The first request resulted in a redirect, Authorization should be removed
        assert received_headers.get(custom_auth_header, "") == custom_auth_token_one, \
            "Custom auth header NOT preserved on same-origin redirect."


@pytest.mark.redirect_auth
def test_custom_auth_class_not_removed_on_same_origin_redirect(test_class,
                                                               request_method,
                                                               custom_auth_header,
                                                               custom_auth_token_one,
                                                               custom_auth_token_two):
    class AuthMockServerRequestHandler(BaseHTTPRequestHandler):
        server_address = None
        request_count = 0
        received_auth = None

        def do_POST(self):
            logger.debug("Received POST request to Auth Mock Server")
            self.send_response(200)
            self.send_header(
                "Content-Type", "application/json; charset=utf-8"
            )
            self.end_headers()
            if self.__class__.request_count == 0:
                self.wfile.write(bytes(json.dumps({"token": custom_auth_token_one}), "utf-8"))
            else:
                self.wfile.write(bytes(json.dumps({"token": custom_auth_token_two}), "utf-8"))
            self.__class__.request_count += 1
            return


    class TargetMockServerRequestHandler(MockServerRequestHandler):
        request_count = 0
        next_server = None

        def send_default_response(self):
            """
            Generic response for tests in this file. Return any received headers
            and body content as a JSON-encoded dictionary with key "headers"
            containing received headers and key "body" with received body.

            :return: None
            """
            if self.__class__.request_count == 0:
                self.__class__.request_count += 1
                logger.debug("Received request")
                logger.debug("First server headers: %s", self.headers)
                self.send_response(301)
                self.send_header(
                    "Content-Type", "application/json; charset=utf-8"
                )
                logger.debug("Redirecting to %s", self.__class__.next_server)
                self.send_header("Location", self.__class__.next_server)
                self.end_headers()
                response_data = {
                    "headers": dict(self.headers),
                    "body": {}
                }
                self.wfile.write(bytes(json.dumps(response_data).encode("utf-8")))
            else:
                logger.debug("Received request")
                logger.debug("Second server headers: %s", self.headers)
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

    class ExampleTokenAuth(requests.auth.AuthBase):
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
            else:
                logger.info("Token already present")

        def get_token(self):
            token_result = requests.post(self.auth_url, auth=(self.username, self.password))
            token = token_result.json()["token"]
            return token

        def __call__(self, r):
            logger.info("Dir of r in __call__: %s", dir(r))
            if hasattr(r, "status_code") and r.status_code == 401:
                logger.error("Status code in __call__ is 401!")
            r.headers[custom_auth_header] = self.token
            self.__class__.header_usage_count += 1
            r.register_hook("response", self.redirect)
            r.register_hook("response", self.reauth)
            return r

        def reauth(self, r, **kwargs):
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
                prep.headers[custom_auth_header] = self.get_token()
                logger.debug("Prep headers:\n%s", prep.headers)
                _r = r.connection.send(prep, **kwargs)
                _r.history.append(r)
                _r.request = prep
                logger.error(prep)
                return _r

            return r

        def redirect(self, r, **kwargs):
            if r.is_redirect and \
                    (urlparse(r.request.url).netloc !=
                     urlparse(r.headers["Location"]).netloc):
                logger.info("Redirect to different origin...")
                r.request.headers = {
                    k: v for k, v in r.request.headers.items() if k != custom_auth_header
                }
            return r

    with test_class() as class_instance:
        # def auth_response_hook(response, **kwargs):  # pylint: disable=unused-argument
        #     logger.info("Entering auth response hook...")
        #     if response.is_redirect and \
        #             (urlparse(response.request.url).netloc !=
        #              urlparse(response.headers["Location"]).netloc):
        #         logger.info("Auth response hook - deleting auth header.")
        #         logger.info("Response headers: %s", response.headers)
        #         response.request.headers = {
        #             k: v for k, v in response.request.headers.items() if k != custom_auth_header
        #         }
        #         return response

        auth_server = BaseHttpServer(handler=AuthMockServerRequestHandler)
        class_instance.auth = ExampleTokenAuth(auth_url=auth_server.url,
                                               username="username",
                                               password="password")
        # class_instance.response_hooks = auth_response_hook
        target_server = BaseHttpServer(handler=TargetMockServerRequestHandler)
        TargetMockServerRequestHandler.next_server = target_server.url

        auth_response = class_instance.request(request_method, target_server.url)
        received_headers = auth_response.json().get("headers")
        logger.info("RECEIVED final: %s", received_headers)
        auth_server.stop_server()
        target_server.stop_server()

        # The first request resulted in a 401, so a reauth should happen and the
        # X-Auth-Token should be for token two.
        assert received_headers.get(custom_auth_header, "") == custom_auth_token_one, \
            "Custom auth header not present in response"
