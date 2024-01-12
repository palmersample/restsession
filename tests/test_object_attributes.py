"""
Test functions for object attributes
"""
# pylint: disable=redefined-outer-name, line-too-long
import logging
import time
import pytest
import requests_toolbelt.sessions
import restsession
import restsession.defaults
import restsession.exceptions
import requests.exceptions
import requests.utils
import requests

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.attrs


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
def test_valid_timeout(test_class, request_method, generic_mock_server):
    """
    Test that setting a timeout is set and honored by the class instance

    :param test_class: Fixture of the class to test
    :param request_method: Fixture of the HTTP verb to test
    :param generic_mock_server: Fixture for the generic mock server
    :return: None
    """
    generic_mock_server.set_handler_response_delay(delay_seconds=2)
    with test_class() as class_instance:
        class_instance.timeout = 1.0
        class_instance.retries = 0
        with pytest.raises(requests.exceptions.ConnectionError) as exc_info:  # pylint: disable=unused-variable
            start_time = time.time()
            class_instance.request(request_method, generic_mock_server.url)

        end_time = time.time() - start_time

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
    """
    Test that attempting to set an invalid timeout value results in an
    InvalidParameterError exception

    :param test_class: Fixture of the class to test
    :return: None
    """
    with test_class() as class_instance:
        with pytest.raises(restsession.exceptions.InvalidParameterError):
            class_instance.timeout = "Invalid string"

#
# def test_invalid_retries(test_class):
#     with test_class() as class_instance:
#         ...
#
#
# def test_invalid_max_redirects(test_class):
#     with test_class() as class_instance:
#         ...
#
#
# def test_invalid_backoff_factor(test_class):
#     with test_class() as class_instance:
#         ...
#
#
# def test_invalid_retry_status_code_list(test_class):
#     with test_class() as class_instance:
#         ...
#
#
# def test_invalid_retry_method_list(test_class):
#     with test_class() as class_instance:
#         ...
#
#
# def test_invalid_respect_retry_headers(test_class):
#     with test_class() as class_instance:
#         ...
#
#
# def test_valid_base_url(test_class):
#     with test_class() as class_instance:
#         ...
#
#
# def test_valid_verify(test_class):
#     with test_class() as class_instance:
#         ...
#
#
# def test_valid_auth(test_class):
#     with test_class() as class_instance:
#         ...
#
#
# def test_valid_headers(test_class):
#     with test_class() as class_instance:
#         ...
#
#
# def test_valid_auth_headers(test_class):
#     with test_class() as class_instance:
#         ...
#
#
# def test_valid_max_reauth(test_class):
#     with test_class() as class_instance:
#         ...
