"""
Test functions for request retries
"""
# pylint: disable=redefined-outer-name, line-too-long, too-many-arguments
import logging
import time
import pytest
import requests_toolbelt.sessions
import restsession.defaults
import restsession.exceptions
import requests.exceptions
import requests.utils

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.retries


@pytest.fixture(params=[2])
def request_retry_count(request):
    """
    Fixture for the number of retries before an exception is raised

    :param request: pytest fixture parameter
    :yields: The next fixture parameter
    """
    yield request.param


@pytest.fixture(params=[0.3, 1.0])
def retry_backoff_factor(request):
    """
    Fixture to test different backoff factors for retries when no Retry-After
    header is present

    :param request: pytest fixture parameter
    :yields: The next backoff factor in the fixture params
    """
    yield request.param


@pytest.fixture(params=restsession.defaults.SESSION_DEFAULTS["retry_status_code_list"])
def retry_status_code(request):
    """
    Fixture for HTTP status codes to retry

    :param request: pytest fixture parameter
    :yields: The next status code in the fixture params
    """
    yield request.param


@pytest.fixture(params=[500])
def retry_invalid_status_code(request):
    """
    Fixture for HTTP status code(s) that should not be retried.

    :param request: pytest fixture parameter
    :yields: The next status code in the fixture params
    """
    yield request.param


@pytest.mark.parametrize("test_class",
                         [
                             pytest.param(requests_toolbelt.sessions.BaseUrlSession,
                                          marks=pytest.mark.xfail(
                                          reason="Requests does not perform retries without an adapter mounted.")
                                          ),
                             restsession.RestSession,
                             restsession.RestSessionSingleton
                         ])
def test_successful_retry(test_class,
                          request_method,
                          request_retry_count,
                          retry_mock_server):
    """
    Test that the mounted Retry adapter successfully retries a request when
    a 429 is returned

    :param test_class: Fixture of the class to test
    :param request_method: Fixture of the HTTP verb to test
    :param request_retry_count: Fixture for the number of retries to test
    :param retry_mock_server: Fixture for the retry mock server
    :return: None
    """
    with test_class() as class_instance:
        class_instance.retries = request_retry_count
        class_instance.backoff_factor = 0.0
        retry_mock_server.set_handler_retries(max_retries=request_retry_count)

        request_response = class_instance.request(request_method, retry_mock_server.url)
        server_retry_count = retry_mock_server.mock_server.RequestHandlerClass.retry_count

        assert server_retry_count == request_retry_count, \
            f"Expected {request_retry_count} retries, " \
            f"server received {server_retry_count}"

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
def test_too_many_respectful_retries(test_class,
                                     request_method,
                                     request_retry_count,
                                     retry_mock_server):
    """
    Test that the mounted Retry adapter properly honors a "Retry-After" header
    in the mock server response.

    :param test_class: Fixture of the class to test
    :param request_method: Fixture of the HTTP verb to test
    :param request_retry_count: Fixture for the number of retries to test
    :param retry_mock_server: Fixture for the retry mock server
    :return: None
    """
    # Expected retry should be the request retry count + 1, as the
    # first request hits and then receives a 429. After experiencing
    # (request_retry_count) responses of 429, the exception will be raised.
    # Each request hitting the server will increment the retry counter
    expected_retry_count = request_retry_count + 1

    with test_class() as class_instance:
        class_instance.retries = request_retry_count
        class_instance.backoff_factor = 0.0
        start_time = time.time()
        with pytest.raises(requests.exceptions.RetryError) as exc_info:  # pylint: disable=unused-variable
            class_instance.request(request_method, retry_mock_server.url)
        end_time = time.time() - start_time

        server_retry_count = retry_mock_server.mock_server.RequestHandlerClass.retry_count

        assert server_retry_count == expected_retry_count, \
            f"Expected {expected_retry_count} retries, " \
            f"server received {server_retry_count}"

        logger.info("Total time for request: %s", end_time)

        assert end_time >= request_retry_count, \
            "Total time of requests should be larger than the request retry count.\n" \
            f"Number of retries: {server_retry_count}\n" \
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
@pytest.mark.disrespect
def test_too_many_disrespectful_retries(test_class,
                                        request_method,
                                        request_retry_count,
                                        retry_mock_server):
    """
    Test that a RetryError is raised when the retry count is exceeded, and
    ignore any "Retry-After" header from the server.

    :param test_class: Fixture of the class to test
    :param request_method: Fixture of the HTTP verb to test
    :param request_retry_count: Fixture for the number of retries to test
    :param retry_mock_server: Fixture for the retry mock server
    :return: None
    """
    # Expected retry should be the configured retry count + 1, as the
    # first request hits and then receives a 429. After experiencing
    # (request_retry_count) responses of 429, the exception will be raised.
    # Each request hitting the server will increment the retry counter
    expected_retry_count = request_retry_count + 1

    with test_class() as class_instance:
        class_instance.retries = request_retry_count
        class_instance.backoff_factor = 0.0
        class_instance.respect_retry_headers = False

        start_time = time.time()
        with pytest.raises(requests.exceptions.RetryError) as exc_info:  # pylint: disable=unused-variable
            class_instance.request(request_method, retry_mock_server.url)

        end_time = time.time() - start_time

        server_retry_count = retry_mock_server.mock_server.RequestHandlerClass.retry_count

        assert server_retry_count == expected_retry_count, \
            f"Expected {expected_retry_count} retries, " \
            f"server received {server_retry_count}"

        logger.info("Total time for request: %s", end_time)

        # assert end_time < MockServerRequestHandler.estimated_backoff, \
        assert end_time < request_retry_count, \
            "Total time of requests should be less than the request retry count.\n" \
            f"Number of retries: {server_retry_count}\n" \
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
def test_retry_backoff_factor(test_class,
                              request_method,
                              request_retry_count,
                              retry_backoff_factor,
                              retry_mock_server):
    """
    Test that the retry backoff factor is honored when Retry-After is ignored
    but a retry is necessary.

    :param test_class: Fixture of the class to test
    :param request_method: Fixture of the HTTP verb to test
    :param request_retry_count: Fixture for the number of retries to test
    :param retry_backoff_factor: Fixture for the backoff factor to test
    :param retry_mock_server: Fixture for the retry mock server
    :return: None
    """
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


        start_time = time.time()
        with pytest.raises(requests.exceptions.RetryError) as exc_info:  # pylint: disable=unused-variable
            class_instance.request(request_method, retry_mock_server.url)

        end_time = time.time() - start_time

        server_retry_count = retry_mock_server.mock_server.RequestHandlerClass.retry_count
        logger.error("ESTIMATED BACKOFF: %s", estimated_backoff)

        assert server_retry_count == expected_retry_count, \
            f"Expected {expected_retry_count} retries, " \
            f"server received {server_retry_count}"

        logger.info("Total time for request: %s", end_time)

        assert end_time < estimated_backoff, \
            "Total time of requests should be less than the request retry count.\n" \
            f"Number of retries: {server_retry_count}\n" \
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
def test_retry_status_code_list(test_class,
                                request_method,
                                request_retry_count,
                                retry_status_code,
                                retry_mock_server):
    """
    Test each status code in the retry status code list to ensure the request
    is retried.

    :param test_class: Fixture of the class to test
    :param request_method: Fixture of the HTTP verb to test
    :param request_retry_count: Fixture for the number of retries to test
    :param retry_status_code: Fixture for the mock server response status code
    :param retry_mock_server: Fixture for the retry mock server
    :return: None
    """
    # Expected retry should be the configured retry count + 1, as the
    # first request hits and then receives a 429. After experiencing
    # (request_retry_count) responses of 429, the exception will be raised.
    # Each request hitting the server will increment the retry counter
    expected_retry_count = request_retry_count + 1

    with test_class() as class_instance:
        class_instance.retries = request_retry_count
        class_instance.backoff_factor = 0.0
        class_instance.respect_retry_headers = False
        retry_mock_server.set_handler_response_code(response_code=retry_status_code)

        start_time = time.time()
        with pytest.raises(requests.exceptions.RetryError) as exc_info:  # pylint: disable=unused-variable
            class_instance.request(request_method, retry_mock_server.url)

        end_time = time.time() - start_time

        server_retry_count = retry_mock_server.mock_server.RequestHandlerClass.retry_count

        assert server_retry_count == expected_retry_count, \
            f"Expected {expected_retry_count} retries, " \
            f"server received {server_retry_count}"

        logger.info("Total time for request: %s", end_time)


@pytest.mark.parametrize("test_class",
                         [
                             pytest.param(requests_toolbelt.sessions.BaseUrlSession,
                                          marks=pytest.mark.xfail(
                                          reason="Requests does not perform retries without an adapter mounted.")
                                          ),
                             restsession.RestSession,
                             restsession.RestSessionSingleton
                         ])
def test_retry_status_code_not_in_list(test_class,
                                       request_method,
                                       request_retry_count,
                                       retry_invalid_status_code,
                                       retry_mock_server):
    """
    Test that a retry is NOT performed when a status code is returned that is
    not in the retry status code list.

    :param test_class: Fixture of the class to test
    :param request_method: Fixture of the HTTP verb to test
    :param request_retry_count: Fixture for the number of retries to test
    :param retry_invalid_status_code: Fixture for the mock server non-retry response
    :param retry_mock_server: Fixture for the retry mock server
    :return: None
    """
    retry_mock_server.set_handler_response_code(response_code=retry_invalid_status_code)

    with test_class() as class_instance:
        class_instance.retries = request_retry_count
        class_instance.backoff_factor = 0.0
        class_instance.respect_retry_headers = False

        with pytest.raises(requests.exceptions.HTTPError):
            class_instance.request(request_method, retry_mock_server.url)


@pytest.mark.parametrize("test_class",
                         [
                             pytest.param(requests_toolbelt.sessions.BaseUrlSession,
                                          marks=pytest.mark.xfail(
                                          reason="Requests does not perform retries without an adapter mounted.")
                                          ),
                             restsession.RestSession,
                             restsession.RestSessionSingleton
                         ])
def test_retry_method_not_in_list(test_class,
                                  request_method,
                                  request_retry_count,
                                  retry_mock_server):
    """
    Test that retries are NOT performed for HTTP methods not present in the
    retry method list.

    :param test_class: Fixture of the class to test
    :param request_method: Fixture of the HTTP verb to test
    :param request_retry_count: Fixture for the number of retries to test
    :param retry_mock_server: Fixture for the retry mock server
    :return: None
    """
    with test_class() as class_instance:
        class_instance.retries = request_retry_count
        class_instance.backoff_factor = 0.0
        class_instance.respect_retry_headers = False
        class_instance.retry_method_list = "GET"
        logger.error(class_instance.retry_method_list)

        if request_method.lower() != "get":
            expected_retry_count = 1
            with pytest.raises(requests.exceptions.HTTPError):
                class_instance.request(request_method, retry_mock_server.url)
        else:
            expected_retry_count = request_retry_count + 1
            with pytest.raises(requests.exceptions.RetryError):
                class_instance.request(request_method, retry_mock_server.url)

        server_retry_count = retry_mock_server.mock_server.RequestHandlerClass.retry_count

        assert server_retry_count == expected_retry_count, \
            f"Expected {expected_retry_count} retries, " \
            f"server received {server_retry_count}"

        logger.debug("Stopping the mock server...")
