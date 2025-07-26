"""
Pytest configuration for this test suite.
"""
import logging
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
import socket
from threading import Thread
import json
import time
from restsession import RestSession, RestSessionSingleton
import pytest

logger = logging.getLogger(__name__)

def pytest_sessionfinish(session, exitstatus):
    """
    Taken from https://github.com/pytest-dev/pytest/issues/2393

    If pytest does not run tests (even when it's expected) when run with the
    '--last-failed --last-failed-no-failures none' arguments, it exits with
    a result of 5 (instead of 0), which causes pipelines to fail.

    Overriding the behavior based on a code example by GitHub user 'yashtodi94'
    to try to get the 5 changed to a zero.

    :param session: Pytest session fixture
    :param exitstatus: Exit status returned by pytest
    :return: None
    """
    if exitstatus == 5:
        session.exitstatus = 0 # Any arbitrary custom status you want to return```

@pytest.fixture(scope="session",
                params=[RestSession,])
def standard_test_class(request):
    """
    Fixture for standard classes (non-singletons)

    :param request: pytest param for this fixture
    :yields: The next class for the test
    """
    yield request.param


@pytest.fixture(scope="session",
                params=[RestSessionSingleton])
def singleton_test_class(request):
    """
    Fixture for singleton classes

    :param request: pytest param for this fixture
    :yields: The next class for the test
    """
    yield request.param


@pytest.fixture(scope="session",
                params=[RestSession,
                        RestSessionSingleton,])
def test_class(request):
    """
    Fixture for all classes to test. Used for most tests where it doesn't
    matter if the class is a singleton.

    :param request: pytest param for this fixture
    :return: The next class for the test
    """
    yield request.param


@pytest.fixture(autouse=True, scope="function")
def reset_singleton():
    """
    Fixture to clear the singleton instances attribute after each test,
    ensuring that each iteration / test gets a clean instance.

    :return: None
    """
    RestSessionSingleton._instances = {}  # pylint: disable=protected-access


@pytest.fixture(scope="session",
                params=["get",
                        "post",
                        "put",
                        "patch",
                        "delete",
                        "trace",
                        "options"])
def request_method(request):
    """
    Fixture for the HTTP method to test.

    :param request: pytest param for this fixture
    :return: The next HTTP verb for the test
    """
    yield request.param


# @pytest.fixture(scope="session")
@pytest.fixture(scope="module")
def generic_mock_server():
    """
    Fixture for the generic HTTP mock server defined below. Use for
    non-specific tests to verify core functionality.

    :return: Instance of BaseHttpServer with the generic handler.
    """
    mock_server = BaseHttpServer(handler=MockServerRequestHandler)
    yield mock_server
    mock_server.stop_server()


@pytest.fixture(scope="function", autouse=True)
def reset_generic_handler():
    """
    Autouse fixture to reset the generic handler class variables for each
    test function.

    :return: None
    """
    MockServerRequestHandler.sleep_time = 0
    MockServerRequestHandler.url_path = None


@pytest.fixture(scope="module")
def redirect_mock_server():
    """
    Fixture for the generic HTTP mock server defined below. Use for
    non-specific tests to verify core functionality.

    :return: Instance of BaseHttpServer with the redirect handler.
    """
    mock_server = BaseHttpServer(handler=RedirectMockServerRequestHandler)
    yield mock_server
    mock_server.stop_server()


@pytest.fixture(scope="function",
                autouse=True)
def reset_redirect_handler():
    """
    Autouse fixture to reset the redirect handler class variables for each
    test function

    :return: None
    """
    RedirectMockServerRequestHandler.next_server = None
    RedirectMockServerRequestHandler.max_redirect = 1
    RedirectMockServerRequestHandler.redirect_count = 0
    RedirectMockServerRequestHandler.response_code = 301


@pytest.fixture(scope="module")
def retry_mock_server():
    """
    Fixture for the generic HTTP mock server defined below. Use for
    testing the Retry adapters.

    :return: Instance of BaseHttpServer with the retry handler.
    """
    mock_server = BaseHttpServer(handler=RetryServerRequestHandler)
    yield mock_server
    mock_server.stop_server()


@pytest.fixture(scope="function",
                autouse=True)
def reset_retry_handler():
    """
    Autouse fixture to reset the retry handler class variables for each
    test function

    :return: None
    """
    # Set max retries to something large so it will perpetually retry unless
    # overridden.
    RetryServerRequestHandler.max_retries = 99
    RetryServerRequestHandler.retry_count = 0
    RetryServerRequestHandler.response_code = 429


class BaseHttpServer:
    """
    Base HTTP server class. When instantiated, __init__ expects a handler
    instance that will process incoming requests.
    """
    mock_servers = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_server()

    def stop_server(self):
        """
        Terminate the mock server and remove the instance from the class
        variable used to track running threads

        :return: None
        """
        logger.info("Stopping server...")
        self.mock_server.shutdown()
        self.mock_server.server_close()
        if class_server_ref := self.__class__.mock_servers[self.mock_server]:
            class_server_ref.join()

        del self.__class__.mock_servers[self.mock_server]
        logger.info("Server stopped!")

    def __init__(self, handler, bind_address="localhost"):
        def get_free_port():
            s = socket.socket(socket.AF_INET, type=socket.SOCK_STREAM)  # pylint: disable=invalid-name
            s.bind((bind_address, 0))
            _, port = s.getsockname()
            s.close()
            return port

        server_port = get_free_port()
        self.mock_server = HTTPServer((bind_address, server_port), handler)
        handler.server_address = f"{bind_address}:{server_port}"

        mock_server_thread = Thread(target=self.mock_server.serve_forever)
        mock_server_thread.daemon = True
        mock_server_thread.start()

        self.url = f"http://{handler.server_address}"
        self.__class__.mock_servers[self.mock_server] = mock_server_thread

    def set_handler_redirect(self, next_server, max_redirect=1):
        """
        Set a "next_server" attribute for the attached request handler. If
        supported, the handler will use this attribute to generate a redirect
        to the specified URL

        :param next_server: URL of the redirect target
        :param max_redirect: Maximum number of redirects to generate
        :return: None
        """
        self.mock_server.RequestHandlerClass.next_server = next_server
        self.mock_server.RequestHandlerClass.max_redirect = max_redirect

    def set_handler_response_code(self, response_code):
        """
        Set the returned HTTP response code to be returned by the attached
        request handler.

        :param response_code: HTTP response code that should be returned
        :return: None
        """
        self.mock_server.RequestHandlerClass.response_code = response_code

    def set_handler_response_delay(self, delay_seconds):
        """
        Set the sleep_time class variable to delay the time between
        initial connection and responding to the client. Used for testing
        timeouts.

        :param delay_seconds: Number of seconds to sleep
        :return: None
        """
        self.mock_server.RequestHandlerClass.sleep_time = delay_seconds

    def set_handler_retries(self, max_retries=1):
        """
        Set a the number of retries for the RetryHandler class

        :param max_retries: Maximum number of retry responses to generate
        :return: None
        """
        self.mock_server.RequestHandlerClass.max_retries = max_retries

    def set_server_target_path(self, target_path):
        """
        Set a target URL path for the request handler class. Used for testing
        the base and explicit URLs for a request.

        :param target_path: Path the handler should respond to
        :return: None
        """
        self.mock_server.RequestHandlerClass.url_path = target_path


class MockServerRequestHandler(BaseHTTPRequestHandler):
    """
    Handler definition for the generic HTTP request handler.

    Define actions for basic HTTP operations here.
    """
    # pylint: disable=invalid-name, useless-return
    server_address = None
    sleep_time = 0
    url_path = None
    # sleep_time = 0
    # request_count = 0
    # received_headers = None

    def send_default_response(self):
        """
        Generic response for tests in this file. Return any received headers
        and body content as a JSON-encoded dictionary with key "headers"
        containing received headers and key "body" with received body.

        :return: None
        """
        if content_len := int(self.headers.get('content-length', 0)) > 0:
            received_body = self.rfile.read(content_len).decode("utf-8")
        else:
            received_body = {}

        logger.debug("Received request to %s", self.path)
        logger.debug("Received headers: %s", self.headers)
        logger.debug("Received body: %s", received_body)
        if getattr(self.__class__, "sleep_time", None):
            time.sleep(self.__class__.sleep_time)

        if target_path := getattr(self.__class__, "url_path", None):
            logger.debug("URL Path: %s", target_path)
            if re.match(target_path, self.path):
                self.send_response(200)
            else:
                self.send_response(404)

        else:
            self.send_response(200)
        self.send_header(
            "Content-Type", "application/json; charset=utf-8"
        )
        self.end_headers()
        response_data = {
            "headers": dict(self.headers),
            "body": received_body
        }
        self.wfile.write(bytes(json.dumps(response_data).encode("utf-8")))

    def do_GET(self):
        """
        Handler for incoming GET requests.

        :return: self.send_default_response()
        """
        return self.send_default_response()

    def do_POST(self):
        """
        Handler for incoming POST requests.

        :return: self.send_default_response()
        """
        return self.send_default_response()

    def do_PUT(self):
        """
        Handler for incoming PUT requests.

        :return: self.send_default_response()
        """
        return self.send_default_response()

    def do_PATCH(self):
        """
        Handler for incoming PATCH requests.

        :return: self.send_default_response()
        """
        return self.send_default_response()

    def do_DELETE(self):
        """
        Handler for incoming DELETE requests.

        :return: self.send_default_response()
        """
        return self.send_default_response()

    def do_TRACE(self):
        """
        Handler for incoming TRACE requests.

        :return: self.send_default_response()
        """
        return self.send_default_response()

    def do_OPTIONS(self):
        """
        Handler for incoming OPTIONS requests.

        :return: self.send_default_response()
        """
        return self.send_default_response()


class RedirectMockServerRequestHandler(MockServerRequestHandler):
    """
    Handler for redirects.
    """
    next_server = None
    max_redirect = 1
    redirect_count = 0
    response_code = 301

    def send_default_response(self):
        """
        Generic response for tests in this file. Return any received headers
        and body content as a JSON-encoded dictionary with key "headers"
        containing received headers and key "body" with received body.

        :return: None
        """
        logger.debug("Received request")
        logger.debug("First server headers: %s", self.headers)
        if content_len := int(self.headers.get('content-length', 0)) > 0:
            received_body = self.rfile.read(content_len).decode("utf-8")
        else:
            received_body = {}

        if self.redirect_count < self.__class__.max_redirect:
            self.send_response(self.__class__.response_code)
            self.send_header(
                "Content-Type", "application/json; charset=utf-8"
            )
            logger.debug("Redirecting to %s", self.__class__.next_server)
            self.send_header("Location", self.__class__.next_server)
            self.end_headers()
            self.__class__.redirect_count += 1
        else:
            self.send_response(200)
            self.send_header(
                "Content-Type", "application/json; charset=utf-8"
            )
            # self.__class__.redirect_count = 0
            self.end_headers()
            response_data = {
                "headers": dict(self.headers),
                "body": received_body
            }
            self.wfile.write(bytes(json.dumps(response_data).encode("utf-8")))


class RetryServerRequestHandler(MockServerRequestHandler):
    """
    Handler definition for the generic HTTP request handler.

    Define actions for basic HTTP operations here.
    """
    # pylint: disable=invalid-name, useless-return
    max_retries = 0
    retry_count = 0
    response_code = 429

    def send_default_response(self):
        """
        Generic response for tests in this file. Return any received headers
        and body content as a JSON-encoded dictionary with key "headers"
        containing received headers and key "body" with received body.

        :return: None
        """
        logger.info("Server received a request, returning 429")
        if self.__class__.retry_count < self.__class__.max_retries:
            self.send_response(self.__class__.response_code)
            self.send_header(
                "Content-Type", "application/json; charset=utf-8"
            )
            self.send_header("Retry-After", "1")
            self.__class__.retry_count += 1
        else:
            self.send_response(200)
        self.end_headers()
