"""
Test functions for object attributes
"""
# pylint: disable=redefined-outer-name, line-too-long
from http.server import BaseHTTPRequestHandler
import json
import logging
import pytest
import requests_toolbelt.sessions
import restsession
import restsession.defaults
import restsession.exceptions
import requests.exceptions
import requests.utils
import requests
from .conftest import BaseHttpServer, MockServerRequestHandler
import time

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.attrs


class TimeoutMockServerHandler(MockServerRequestHandler):
    """
    Handler definition for the generic HTTP request handler.

    Define actions for basic HTTP operations here.
    """
    # pylint: disable=invalid-name, useless-return
    server_address = None
    request_count = 0
    received_headers = None

    def send_default_response(self):
        """
        Generic response for tests in this file. Return any received headers
        and body content as a JSON-encoded dictionary with key "headers"
        containing received headers and key "body" with received body.

        :return: None
        """
        logger.debug("Received request")
        logger.debug("MockServerRequestHandler headers: %s", self.headers)
        logger.debug("Starting sleep at %s", time.time())
        time.sleep(2)
        logger.debug("Stopping sleep at %s", time.time())
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


@pytest.fixture
def timeout_mock_server():
    """
    Start the mock server for incoming requests

    :return: BaseHttpServer instance with this test's request handler
    """
    # Set max redirect to a high value so it's endless. Adjust for success
    # testing.
    return BaseHttpServer(handler=TimeoutMockServerHandler)


@pytest.mark.parametrize("test_class",
                         [
                             pytest.param(requests_toolbelt.sessions.BaseUrlSession,
                                          marks=pytest.mark.xfail(
                                          reason="Timeout not honored on a Requests Session object "
                                                 "without a mounted adapter.")
                                          ),
                             restsession.RestSession,
                             restsession.RestSessionSingleton
                         ])
def test_valid_timeout(test_class, request_method, timeout_mock_server):
    with (test_class() as class_instance):
        class_instance.timeout = 1.0
        class_instance.retries = 0
        with pytest.raises(requests.exceptions.ConnectionError) as exc_info:
            start_time = time.time()
            class_instance.request(request_method, timeout_mock_server.url)

        end_time = time.time() - start_time
        timeout_mock_server.stop_server()

        logger.error("End time: %s", end_time)
        assert round(end_time, 1) == class_instance.timeout, \
            f"Expected end time to be near {class_instance.timeout}, got {end_time}"

@pytest.mark.parametrize("test_class",
                         [
                             pytest.param(requests_toolbelt.sessions.BaseUrlSession,
                                          marks=pytest.mark.xfail(
                                          reason="Requests does not validate that attributes are valid.")
                                          ),
                             restsession.RestSession,
                             restsession.RestSessionSingleton
                         ])
def test_invalid_timeout(test_class):
    with test_class() as class_instance:
        with pytest.raises(restsession.exceptions.InvalidParameterError):
            class_instance.timeout = "Invalid string"


def test_invalid_retries(test_class):
    with test_class() as class_instance:
        ...


def test_invalid_max_redirects(test_class):
    with test_class() as class_instance:
        ...


def test_invalid_backoff_factor(test_class):
    with test_class() as class_instance:
        ...


def test_invalid_retry_status_code_list(test_class):
    with test_class() as class_instance:
        ...


def test_invalid_retry_method_list(test_class):
    with test_class() as class_instance:
        ...


def test_invalid_respect_retry_headers(test_class):
    with test_class() as class_instance:
        ...


def test_valid_base_url(test_class):
    with test_class() as class_instance:
        ...


def test_valid_verify(test_class):
    with test_class() as class_instance:
        ...


def test_valid_auth(test_class):
    with test_class() as class_instance:
        ...


def test_valid_headers(test_class):
    with test_class() as class_instance:
        ...


def test_valid_auth_headers(test_class):
    with test_class() as class_instance:
        ...


def test_valid_max_reauth(test_class):
    with test_class() as class_instance:
        ...