"""
Test functions for request redirects
"""
# pylint: disable=redefined-outer-name, line-too-long
import logging
import re

import pytest
import requests.exceptions
import requests.utils
import requests_toolbelt.sessions


import restsession.exceptions

logger = logging.getLogger(__name__)


pytestmark = pytest.mark.requests

URL_REGEX = re.compile(r"^(/\w+)(.*)$")

@pytest.fixture
def request_url_path():
    """
    Fixture to provide the URL path for request testing

    :return: str - arbitrary path to use for test server
    """
    return "/api/request/path"


# @pytest.fixture(params=[301, 302, 303, 307, 308])
# def redirect_response_code(request):
#     """
#     Fixture to test various redirect response codes.
#
#     :param request: pytest fixture param
#     :return: next response code in the fixture param list
#     """
#     yield request.param

@pytest.mark.parametrize("test_class",
                         [
                             pytest.param(requests_toolbelt.sessions.BaseUrlSession,
                                          marks=pytest.mark.xfail(
                                          reason="Requests does not validate the base URL")
                                          ),
                             restsession.RestSession,
                             restsession.RestSessionSingleton
                         ])
def test_invalid_base_url(test_class,
                          request_method,
                          request_url_path):
    """
    Test that providing an invalid (non-HTTP/HTTPS) URL as the base_url raises
    an exception.

    :param test_class: Fixture of the class to test
    :param request_method: Fixture of the HTTP verb to test
    :param request_url_path: Fixture for the URL path to test
    :return: None
    """
    with test_class() as class_instance:
        with pytest.raises(restsession.exceptions.InvalidParameterError):
            class_instance.base_url = request_url_path


def test_explicit_url(test_class,
                      generic_mock_server,
                      request_method,
                      request_url_path):
    """
    Test request to an explicit (non-baseurl) destination

    :param test_class: Fixture of the class to test
    :param generic_mock_server: Fixture for the generic mock server
    :param request_method: Fixture of the HTTP verb to test
    :param request_url_path: Fixture for the URL path to test
    :return: None
    """
    with test_class() as class_instance:
        target_server = generic_mock_server
        target_server.set_server_target_path(target_path=request_url_path)
        request_url = f"{target_server.url}{request_url_path}"
        response = class_instance.request(request_method, request_url)
        assert response.ok, f"Expected a success, got {response.status_code}"


def test_base_url(test_class,
                  generic_mock_server,
                  request_method,
                  request_url_path):
    """
    Test request to an explicit (non-baseurl) destination

    :param test_class: Fixture of the class to test
    :param generic_mock_server: Fixture for the generic mock server
    :param request_method: Fixture of the HTTP verb to test
    :param request_url_path: Fixture for the URL path to test
    :return: None
    """
    target_server = generic_mock_server
    target_server.set_server_target_path(target_path=request_url_path)

    with test_class(base_url=target_server.url) as class_instance:
        request_url = request_url_path
        response = class_instance.request(request_method, request_url)
        assert response.ok, f"Expected a success, got {response.status_code}"


@pytest.mark.parametrize("test_class",
                         [
                             pytest.param(requests_toolbelt.sessions.BaseUrlSession,
                                          marks=pytest.mark.xfail(
                                          reason="Exception will not be raised from BaseURLSession")
                                          ),
                             restsession.RestSession,
                             restsession.RestSessionSingleton
                         ])
def test_base_url_bad_urljoin(test_class,
                              generic_mock_server,
                              request_method,
                              request_url_path):
    """
    Test request to an explicit (non-baseurl) destination

    :param test_class: Fixture of the class to test
    :param generic_mock_server: Fixture for the generic mock server
    :param request_method: Fixture of the HTTP verb to test
    :param request_url_path: Fixture for the URL path to test
    :return: None
    """
    target_server = generic_mock_server
    target_server.set_server_target_path(target_path=request_url_path)
    base_url = f"{target_server.url.rstrip('/')}{URL_REGEX.match(request_url_path).groups()[0]}"
    target_path = URL_REGEX.match(request_url_path).groups()[1]
    with test_class(base_url=base_url) as class_instance:
        with pytest.raises(requests.exceptions.HTTPError):
            class_instance.request(request_method, target_path)


@pytest.mark.parametrize("test_class",
                         [
                             pytest.param(requests_toolbelt.sessions.BaseUrlSession,
                                          marks=pytest.mark.xfail(
                                          reason="BaseUrlSession does not support always_relative_url")
                                          ),
                             restsession.RestSession,
                             restsession.RestSessionSingleton
                         ])
def test_always_relative_url(test_class,
                             generic_mock_server,
                             request_method,
                             request_url_path):
    """
    Test request to an explicit (non-baseurl) destination

    :param test_class: Fixture of the class to test
    :param generic_mock_server: Fixture for the generic mock server
    :param request_method: Fixture of the HTTP verb to test
    :param request_url_path: Fixture for the URL path to test
    :return: None
    """
    target_server = generic_mock_server
    target_server.set_server_target_path(target_path=request_url_path)
    base_url = f"{target_server.url.rstrip('/')}{URL_REGEX.match(request_url_path).groups()[0]}"
    target_path = URL_REGEX.match(request_url_path).groups()[1]
    with test_class(base_url=base_url) as class_instance:
        class_instance.always_relative_url = True
        logger.info("Base URL: %s", base_url)
        logger.info("Target path: %s", target_path)
        response = class_instance.request(request_method, target_path)

        assert response.ok, \
            f"Expecting successful response, instead got '{response.status_code}'"


def test_base_url_good_urljoin(test_class,
                               generic_mock_server,
                               request_method,
                               request_url_path):
    """
    Test request to an explicit (non-baseurl) destination

    :param test_class: Fixture of the class to test
    :param generic_mock_server: Fixture for the generic mock server
    :param request_method: Fixture of the HTTP verb to test
    :param request_url_path: Fixture for the URL path to test
    :return: None
    """
    target_server = generic_mock_server
    target_server.set_server_target_path(target_path=request_url_path)
    base_url = f"{target_server.url.rstrip('/')}{URL_REGEX.match(request_url_path).groups()[0]}/"
    target_path = URL_REGEX.match(request_url_path).groups()[1].lstrip("/")
    with (test_class(base_url=base_url) as class_instance):
        response = class_instance.request(request_method, target_path)

        assert response.ok, \
            f"Expecting successful response, instead got '{response.status_code}'"



#
# def test_successful_redirect(test_class,
#                              request_method,
#                              redirect_response_code,
#                              request_redirect_count,
#                              redirect_mock_server):
#     """
#
#     :param test_class: Fixture of the class to test
#     :param request_method: Fixture of the HTTP verb to test
#     :param redirect_response_code: Fixture for the mock server response code
#     :param request_redirect_count: Fixture for the number of redirects
#     :param redirect_mock_server: Fixture for the redirect mock server
#     :return: None
#     """
#
#     # Expected redirect should be the configured redirect count, as a
#     # 200 should be returned once the count is reached.
#     redirect_mock_server.set_handler_redirect(next_server=redirect_mock_server.url,
#                                               max_redirect=request_redirect_count)
#     redirect_mock_server.set_handler_response_code(response_code=redirect_response_code)
#
#     with test_class() as class_instance:
#         class_instance.max_redirects = request_redirect_count
#         logger.info(class_instance.max_redirects)
#
#         request_response = class_instance.request(request_method, redirect_mock_server.url)
#         server_redirect_count = redirect_mock_server.mock_server.RequestHandlerClass.redirect_count
#         logger.error("SERVER COUNT: %s", server_redirect_count)
#
#         assert server_redirect_count == request_redirect_count, \
#             f"Expected {request_redirect_count} retries, " \
#             f"server received {server_redirect_count}"
#
#         assert request_response.ok, \
#             f"Expected a successful response code, got: {request_response.status_code}"
#
#
# def test_too_many_redirects(test_class,
#                             request_method,
#                             redirect_response_code,
#                             request_redirect_count,
#                             redirect_mock_server):
#     """
#
#     :param test_class: Fixture of the class to test
#     :param request_method: Fixture of the HTTP verb to test
#     :param redirect_response_code: Fixture for the mock server response code
#     :param request_redirect_count: Fixture for the number of redirects
#     :param redirect_mock_server: Fixture for the redirect mock server
#     :return: None
#     """
#     # Expected redirect should be the configured redirect count + 1, as a
#     # redirect should be sent until the end - no successful response will
#     # be encountered.
#     expected_redirect_count = request_redirect_count + 1
#     redirect_mock_server.set_handler_redirect(next_server=redirect_mock_server.url,
#                                               max_redirect=expected_redirect_count)
#     redirect_mock_server.set_handler_response_code(response_code=redirect_response_code)
#
#     with test_class() as class_instance:
#         class_instance.max_redirects = request_redirect_count
#
#         with pytest.raises(requests.exceptions.TooManyRedirects) as exc_info:
#             logger.debug("TooManyRedirects raised")
#             class_instance.request(request_method, redirect_mock_server.url)
#         server_redirect_count = redirect_mock_server.mock_server.RequestHandlerClass.redirect_count
#
#         assert server_redirect_count == expected_redirect_count, \
#             f"Expected {request_redirect_count} retries, " \
#             f"server received {server_redirect_count}"
#
#         assert not 200 <= exc_info.value.response.status_code <= 299, \
#             f"Expected a successful response code, got: {exc_info.value.response.status_code}"
