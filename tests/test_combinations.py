"""
Testscript for combinations of request types (redirect and retry, retry
and redirect, various auth scenarios)
"""
# pylint: disable=redefined-outer-name, line-too-long
import logging
import pytest
import requests_toolbelt.sessions
import restsession
import restsession.defaults
import restsession.exceptions
from .conftest import BaseHttpServer, MockServerRequestHandler


logger = logging.getLogger(__name__)

pytestmark = pytest.mark.combinations


class ComboServerRequestHandler(MockServerRequestHandler):
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
    # 0 = No redirect. Otherwise, redirect after (n) requests to target
    redirect_after_requests = 0
    redirect_target = None

    def send_default_response(self):
        """
        Generic response for tests in this file. Return any received headers
        and body content as a JSON-encoded dictionary with key "headers"
        containing received headers and key "body" with received body.

        :return: None
        """
        if (self.__class__.redirect_after_requests and
                self.__class__.request_count == self.__class__.redirect_after_requests):
            if self.__class__.redirect_target:
                logger.info("Sending redirect to %s",
                            self.__class__.redirect_target)
                self.send_response(301)
                self.send_header("Location", self.__class__.redirect_target)
                self.__class__.request_count += 1
                self.__class__.retry_count += 1

        elif self.__class__.request_count < self.__class__.max_retries:
            self.send_response(self.__class__.response_code)
            self.send_header("Retry-After", "1")
            self.__class__.request_count += 1
            self.__class__.retry_count += 1

        else:
            self.send_response(200)
        self.end_headers()


@pytest.fixture(scope="module")
def combo_mock_server():
    """
    Start the mock server for incoming requests

    :return: BaseHttpServer instance with this test's request handler
    """
    return BaseHttpServer(handler=ComboServerRequestHandler)


@pytest.fixture(scope="function", autouse=True)
def reset_combo_mock_server():
    """
    Reset the class variables of the combo mock server for each test iteration

    :return: None
    """
    # Max retries should just be something big. Can adjust for any test that
    # checks for a 200 after retry
    ComboServerRequestHandler.max_retries = 99
    ComboServerRequestHandler.request_count = 0
    ComboServerRequestHandler.response_code = 429
    ComboServerRequestHandler.retry_count = 0
    ComboServerRequestHandler.server_address = None
    ComboServerRequestHandler.redirect_after_requests = 0
    ComboServerRequestHandler.redirect_target = None


@pytest.mark.parametrize("test_class",
                         [
                             pytest.param(requests_toolbelt.sessions.BaseUrlSession,
                                          marks=pytest.mark.xfail(
                                              reason="Requests does not perform retries without an adapter mounted.")
                                          ),
                             restsession.RestSession,
                             restsession.RestSessionSingleton
                         ])
def test_redirect_then_retry(test_class, request_method, redirect_mock_server, combo_mock_server):
    """
    Test that a successful request can be made after a redirect then forced
    retry.

    :param test_class:
    :param redirect_mock_server:
    :param retry_mock_server:
    :return:
    """
    redirect_mock_server.set_handler_redirect(next_server=combo_mock_server.url, max_redirect=1)
    ComboServerRequestHandler.max_retries = 2

    with test_class() as class_instance:
        request_response = class_instance.request(request_method, redirect_mock_server.url)

        assert request_response.ok, \
            f"Expected a successful response, received {request_response.status_code}"


@pytest.mark.parametrize("test_class",
                         [
                             pytest.param(requests_toolbelt.sessions.BaseUrlSession,
                                          marks=pytest.mark.xfail(
                                              reason="Requests does not perform retries without an adapter mounted.")
                                          ),
                             restsession.RestSession,
                             restsession.RestSessionSingleton
                         ])
def test_retry_then_redirect(test_class, request_method, redirect_mock_server, combo_mock_server):
    """
    Test that a successful request can be made after a forced retry and redirect.

    :param test_class:
    :param redirect_mock_server:
    :param retry_mock_server:
    :return:
    """
    redirect_mock_server.set_handler_redirect(next_server=redirect_mock_server.url, max_redirect=2)
    combo_mock_server.set_handler_redirect(next_server=redirect_mock_server.url, max_redirect=2)
    combo_mock_server.set_handler_retries(max_retries=2)

    with test_class() as class_instance:
        request_response = class_instance.request(request_method, combo_mock_server.url)

        assert request_response.ok, \
            f"Expected a successful response, received {request_response.status_code}"
