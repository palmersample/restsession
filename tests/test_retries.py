"""
Test functions for request retries
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
from .conftest import BaseHttpServer, MockServerRequestHandler
import time


logger = logging.getLogger(__name__)


pytestmark = pytest.mark.retries

# @pytest.fixture(params=[2, 3, 4])
@pytest.fixture(params=[2])
def request_retry_count(request):
    yield request.param


@pytest.fixture(params=[0.3, 1.0])
def retry_backoff_factor(request):
    yield request.param


@pytest.fixture(params=restsession.defaults.SESSION_DEFAULTS["retry_status_code_list"])
def retry_status_code(request):
    yield request.param


@pytest.fixture
def retry_invalid_status_code():
    return 500


class RetryServerRequestHandler(MockServerRequestHandler):
    """
    Handler definition for the generic HTTP request handler.

    Define actions for basic HTTP operations here.
    """
    # pylint: disable=invalid-name, useless-return
    max_retries = 0
    response_code = 429
    server_address = None
    request_count = 0
    retry_count = 0

    def send_default_response(self):
        """
        Generic response for tests in this file. Return any received headers
        and body content as a JSON-encoded dictionary with key "headers"
        containing received headers and key "body" with received body.

        :return: None
        """
        self.__class__.request_count += 1
        self.__class__.retry_count += 1
        logger.info("Server received a request, returning 429")
        if self.__class__.request_count < self.__class__.max_retries:
            self.send_response(self.__class__.response_code)
            self.send_header(
                "Content-Type", "application/json; charset=utf-8"
            )
            self.send_header("Retry-After", "1")
        else:
            self.send_response(200)
        self.end_headers()
        return


@pytest.fixture
def mock_server():
    """
    Start the mock server for incoming requests

    :return: BaseHttpServer instance with this test's request handler
    """
    # Max retries should just be something big. Can adjust for any test that
    # checks for a 200 after retry
    RetryServerRequestHandler.max_retries = 99
    RetryServerRequestHandler.request_count = 0
    RetryServerRequestHandler.response_code = 429
    RetryServerRequestHandler.retry_count = 0
    RetryServerRequestHandler.server_address = None
    return BaseHttpServer(handler=RetryServerRequestHandler)


@pytest.mark.parametrize("test_class",
                         [
                             pytest.param(requests_toolbelt.sessions.BaseUrlSession,
                                          marks=pytest.mark.xfail(
                                          reason="Requests does not perform retries without an adapter mounted.")
                                          ),
                             restsession.RestSession,
                             restsession.RestSessionSingleton
                         ])
@pytest.mark.good_one
def test_successful_retry(test_class, request_method, request_retry_count, mock_server):

    # Expected retry should be the configured retry count + 1, as the
    # first request hits and then receives a 429. After experiencing
    # (request_retry_count) responses of 429, the exception will be raised.
    # Each request hitting the server will increment the retry counter
    expected_retry_count = request_retry_count + 1

    with test_class() as class_instance:
        class_instance.retries = request_retry_count
        class_instance.backoff_factor = 0.0
        RetryServerRequestHandler.max_retries = request_retry_count

        request_response = class_instance.request(request_method, mock_server.url)
        mock_server.stop_server()

        assert RetryServerRequestHandler.retry_count == request_retry_count, \
            f"Expected {expected_retry_count} retries, " \
            f"server received {RetryServerRequestHandler.retry_count}"

        assert request_response.ok, \
            f"Expected a successful response code, got: {request_response.status_code}"


@pytest.mark.parametrize("test_class",
                         [
                             pytest.param(requests_toolbelt.sessions.BaseUrlSession,
                                          marks=pytest.mark.xfail(
                                          reason="Requests does not perform retries without an adapter mounted.")
                                          ),
                             restsession.RestSession,
                             restsession.RestSessionSingleton
                         ])
@pytest.mark.respect
def test_too_many_respectful_retries(test_class, request_method, request_retry_count, mock_server):

    # Expected retry should be the configured retry count + 1, as the
    # first request hits and then receives a 429. After experiencing
    # (request_retry_count) responses of 429, the exception will be raised.
    # Each request hitting the server will increment the retry counter
    expected_retry_count = request_retry_count + 1

    with test_class() as class_instance:
        class_instance.retries = request_retry_count
        class_instance.backoff_factor = 0.0
        try:
            start_time = time.time()
            class_instance.request(request_method, mock_server.url)
        # RetryError will be thrown after the last retry with no response.
        except requests.exceptions.RetryError:
            end_time = time.time() - start_time
        mock_server.stop_server()

        assert RetryServerRequestHandler.retry_count == expected_retry_count, \
            f"Expected {expected_retry_count} retries, " \
            f"server received {RetryServerRequestHandler.retry_count}"

        logger.info("Total time for request: %s", end_time)

        assert end_time >= request_retry_count, \
            "Total time of requests should be larger than the request retry count.\n" \
            f"Number of retries: {RetryServerRequestHandler.retry_count}\n" \
            f"Elapsed time: {end_time}"

        assert RetryServerRequestHandler.retry_count == expected_retry_count, \
            f"Expected {expected_retry_count} retries, " \
            f"server received {RetryServerRequestHandler.retry_count}"


@pytest.mark.parametrize("test_class",
                         [
                             pytest.param(requests_toolbelt.sessions.BaseUrlSession,
                                          marks=pytest.mark.xfail(
                                          reason="Requests does not perform retries without an adapter mounted.")
                                          ),
                             restsession.RestSession,
                             restsession.RestSessionSingleton
                         ])
@pytest.mark.disrespect
def test_too_many_disrespectful_retries(test_class, request_method, request_retry_count, mock_server):

    # Expected retry should be the configured retry count + 1, as the
    # first request hits and then receives a 429. After experiencing
    # (request_retry_count) responses of 429, the exception will be raised.
    # Each request hitting the server will increment the retry counter
    expected_retry_count = request_retry_count + 1

    with test_class() as class_instance:
        class_instance.retries = request_retry_count
        class_instance.backoff_factor = 0.0
        class_instance.respect_retry_headers = False

        try:
            start_time = time.time()
            class_instance.request(request_method, mock_server.url)
        # RetryError will be thrown after the last retry with no response.
        except requests.exceptions.RetryError:
            end_time = time.time() - start_time
        # test_server.stop_mock_server(mock_server=test_server)
        mock_server.stop_server()
        # logger.error("ESTIMATED BACKOFF: %s", mock_server.estimated_backoff)

        assert RetryServerRequestHandler.retry_count == expected_retry_count, \
            f"Expected {expected_retry_count} retries, " \
            f"server received {RetryServerRequestHandler.retry_count}"

        logger.info("Total time for request: %s", end_time)

        # assert end_time < MockServerRequestHandler.estimated_backoff, \
        assert end_time < request_retry_count, \
            "Total time of requests should be less than the request retry count.\n" \
            f"Number of retries: {mock_server.__class__.retry_count}\n" \
            f"Elapsed time: {end_time}"

        # assert end_time < request_retry_count, \
        #     "Total time of requests should be less than the request retry count.\n" \
        #     f"Number of retries: {MockServerRequestHandler.retry_count}\n" \
        #     f"Elapsed time: {end_time}"

        # assert MockServerRequestHandler.retry_count == expected_retry_count, \
        #     f"Expected {expected_retry_count} retries, " \
        #     f"server received {MockServerRequestHandler.retry_count}"

@pytest.mark.parametrize("test_class",
                         [
                             pytest.param(requests_toolbelt.sessions.BaseUrlSession,
                                          marks=pytest.mark.xfail(
                                          reason="Requests does not perform retries without an adapter mounted.")
                                          ),
                             restsession.RestSession,
                             restsession.RestSessionSingleton
                         ])
@pytest.mark.backoff
def test_retry_backoff_factor(test_class, request_method, request_retry_count, retry_backoff_factor, mock_server):
    # class MockServerRequestHandler(BaseHTTPRequestHandler):
    #     backoff_factor = retry_backoff_factor
    #     estimated_backoff = 0.0
    #     server_address = None
    #     request_count = 0
    #     retry_count = 0
    #
    #     def do_GET(self):
    #         self.__class__.estimated_backoff = self.__class__.backoff_factor * (2 ** (self.__class__.request_count))
    #         logger.error("Current estimated backoff: %s", self.__class__.estimated_backoff)
    #         self.__class__.request_count += 1
    #         self.__class__.retry_count += 1
    #         logger.info("Server received a request, returning 429")
    #         logger.info(time.time())
    #         self.send_response(429)
    #         self.send_header(
    #             "Content-Type", "application/json; charset=utf-8"
    #         )
    #         self.send_header("Retry-After", "10")
    #         self.end_headers()
    #         return
    #
    # test_server = BaseHttpServer(handler=MockServerRequestHandler)
    # test_url = f"http://{MockServerRequestHandler.server_address}"

    # Expected retry should be the configured retry count + 1, as the
    # first request hits and then receives a 429. After experiencing
    # (request_retry_count) responses of 429, the exception will be raised.
    # Each request hitting the server will increment the retry counter
    expected_retry_count = request_retry_count + 1

    estimated_backoff = 0.0
    for request_count in range(0, request_retry_count):
        estimated_backoff += retry_backoff_factor * (2 ** request_count)

    with test_class() as class_instance:
        class_instance.retries = request_retry_count
        class_instance.backoff_factor = retry_backoff_factor
        class_instance.respect_retry_headers = False

        try:
            start_time = time.time()
            class_instance.request(request_method, mock_server.url)
        # RetryError will be thrown after the last retry with no response.
        except requests.exceptions.RetryError:
            end_time = time.time() - start_time
        mock_server.stop_server()

        logger.error("ESTIMATED BACKOFF: %s", estimated_backoff)

        assert RetryServerRequestHandler.retry_count == expected_retry_count, \
            f"Expected {expected_retry_count} retries, " \
            f"server received {RetryServerRequestHandler.retry_count}"

        logger.info("Total time for request: %s", end_time)

        assert end_time < estimated_backoff, \
            "Total time of requests should be less than the request retry count.\n" \
            f"Number of retries: {RetryServerRequestHandler.retry_count}\n" \
            f"Elapsed time: {end_time}"

@pytest.mark.parametrize("test_class",
                         [
                             pytest.param(requests_toolbelt.sessions.BaseUrlSession,
                                          marks=pytest.mark.xfail(
                                          reason="Requests does not perform retries without an adapter mounted.")
                                          ),
                             restsession.RestSession,
                             restsession.RestSessionSingleton
                         ])
@pytest.mark.status
def test_retry_status_code_list(test_class, request_method, request_retry_count, retry_status_code, mock_server):

    # Expected retry should be the configured retry count + 1, as the
    # first request hits and then receives a 429. After experiencing
    # (request_retry_count) responses of 429, the exception will be raised.
    # Each request hitting the server will increment the retry counter
    expected_retry_count = request_retry_count + 1

    with test_class() as class_instance:
        class_instance.retries = request_retry_count
        class_instance.backoff_factor = 0.0
        class_instance.respect_retry_headers = False
        RetryServerRequestHandler.response_code = retry_status_code
        try:
            start_time = time.time()
            class_instance.request(request_method, mock_server.url)
        # RetryError will be thrown after the last retry with no response.
        except requests.exceptions.RetryError:
            end_time = time.time() - start_time
        mock_server.stop_server()

        # logger.error("ESTIMATED BACKOFF: %s", MockServerRequestHandler.estimated_backoff)

        assert RetryServerRequestHandler.retry_count == expected_retry_count, \
            f"Expected {expected_retry_count} retries, " \
            f"server received {RetryServerRequestHandler.retry_count}"

        logger.info("Total time for request: %s", end_time)

        # assert end_time < MockServerRequestHandler.estimated_backoff, \
        # assert end_time < estimated_backoff, \
        #     "Total time of requests should be less than the request retry count.\n" \
        #     f"Number of retries: {RedirectServerRequestHandler.retry_count}\n" \
        #     f"Elapsed time: {end_time}"


@pytest.mark.parametrize("test_class",
                         [
                             pytest.param(requests_toolbelt.sessions.BaseUrlSession,
                                          marks=pytest.mark.xfail(
                                          reason="Requests does not perform retries without an adapter mounted.")
                                          ),
                             restsession.RestSession,
                             restsession.RestSessionSingleton
                         ])
@pytest.mark.status
def test_retry_status_code_not_in_list(test_class, request_method, request_retry_count, retry_status_code, retry_invalid_status_code, mock_server):

    RetryServerRequestHandler.response_code = retry_invalid_status_code

    with test_class() as class_instance:
        class_instance.retries = request_retry_count
        class_instance.backoff_factor = 0.0
        class_instance.respect_retry_headers = False

        with pytest.raises(requests.exceptions.HTTPError):
            class_instance.request(request_method, mock_server.url)

        logger.debug("Stopping the mock server...")
        mock_server.stop_server()


@pytest.mark.parametrize("test_class",
                         [
                             pytest.param(requests_toolbelt.sessions.BaseUrlSession,
                                          marks=pytest.mark.xfail(
                                          reason="Requests does not perform retries without an adapter mounted.")
                                          ),
                             restsession.RestSession,
                             restsession.RestSessionSingleton
                         ])
@pytest.mark.status
def test_retry_method_not_in_list(test_class, request_method, request_retry_count, retry_status_code, retry_invalid_status_code, mock_server):

    with test_class() as class_instance:
        class_instance.retries = request_retry_count
        class_instance.backoff_factor = 0.0
        class_instance.respect_retry_headers = False
        class_instance.retry_method_list = "GET"
        logger.error(class_instance.retry_method_list)

        if request_method.lower() != "get":
            expected_retry_count = 1
            with pytest.raises(requests.exceptions.HTTPError):  # HTTP Error AND RetryError are raised?
                class_instance.request(request_method, mock_server.url)
        else:
            expected_retry_count = request_retry_count + 1
            with pytest.raises(requests.exceptions.RetryError):
                class_instance.request(request_method, mock_server.url)

        assert RetryServerRequestHandler.retry_count == expected_retry_count, \
            f"Expected {expected_retry_count} retries, " \
            f"server received {RetryServerRequestHandler.retry_count}"

        logger.debug("Stopping the mock server...")
        mock_server.stop_server()
