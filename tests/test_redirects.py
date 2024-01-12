"""
Test functions for request redirects
"""
# pylint: disable=redefined-outer-name, line-too-long
import logging
import pytest
import requests.exceptions
import requests.utils

logger = logging.getLogger(__name__)


pytestmark = pytest.mark.redirects


@pytest.fixture
def request_redirect_count():
    """
    Fixture to define the count of request redirects.

    :return: int - number of redirects
    """
    return 3


@pytest.fixture(params=[301, 302, 303, 307, 308])
def redirect_response_code(request):
    """
    Fixture to test various redirect response codes.

    :param request: pytest fixture param
    :return: next response code in the fixture param list
    """
    yield request.param


def test_successful_redirect(test_class,
                             request_method,
                             redirect_response_code,
                             request_redirect_count,
                             redirect_mock_server):
    """

    :param test_class: Fixture of the class to test
    :param request_method: Fixture of the HTTP verb to test
    :param redirect_response_code: Fixture for the mock server response code
    :param request_redirect_count: Fixture for the number of redirects
    :param redirect_mock_server: Fixture for the redirect mock server
    :return: None
    """

    # Expected redirect should be the configured redirect count, as a
    # 200 should be returned once the count is reached.
    redirect_mock_server.set_handler_redirect(next_server=redirect_mock_server.url,
                                              max_redirect=request_redirect_count)
    redirect_mock_server.set_handler_response_code(response_code=redirect_response_code)

    with test_class() as class_instance:
        class_instance.max_redirects = request_redirect_count
        logger.info(class_instance.max_redirects)

        request_response = class_instance.request(request_method, redirect_mock_server.url)
        server_redirect_count = redirect_mock_server.mock_server.RequestHandlerClass.redirect_count
        logger.error("SERVER COUNT: %s", server_redirect_count)

        assert server_redirect_count == request_redirect_count, \
            f"Expected {request_redirect_count} retries, " \
            f"server received {server_redirect_count}"

        assert request_response.ok, \
            f"Expected a successful response code, got: {request_response.status_code}"


def test_too_many_redirects(test_class,
                            request_method,
                            redirect_response_code,
                            request_redirect_count,
                            redirect_mock_server):
    """

    :param test_class: Fixture of the class to test
    :param request_method: Fixture of the HTTP verb to test
    :param redirect_response_code: Fixture for the mock server response code
    :param request_redirect_count: Fixture for the number of redirects
    :param redirect_mock_server: Fixture for the redirect mock server
    :return: None
    """
    # Expected redirect should be the configured redirect count + 1, as a
    # redirect should be sent until the end - no successful response will
    # be encountered.
    expected_redirect_count = request_redirect_count + 1
    redirect_mock_server.set_handler_redirect(next_server=redirect_mock_server.url,
                                              max_redirect=expected_redirect_count)
    redirect_mock_server.set_handler_response_code(response_code=redirect_response_code)

    with test_class() as class_instance:
        class_instance.max_redirects = request_redirect_count

        with pytest.raises(requests.exceptions.TooManyRedirects) as exc_info:
            logger.debug("TooManyRedirects raised")
            class_instance.request(request_method, redirect_mock_server.url)
        server_redirect_count = redirect_mock_server.mock_server.RequestHandlerClass.redirect_count

        assert server_redirect_count == expected_redirect_count, \
            f"Expected {request_redirect_count} retries, " \
            f"server received {server_redirect_count}"

        assert not 200 <= exc_info.value.response.status_code <= 299, \
            f"Expected a successful response code, got: {exc_info.value.response.status_code}"
