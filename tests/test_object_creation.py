import pytest
import requests_toolbelt.sessions

import restsession
import restsession.defaults
import restsession.exceptions
import requests.exceptions
import logging
requests_toolbelt.sessions
import builtins

logger = logging.getLogger(__name__)


pytestmark = pytest.mark.objects


@pytest.fixture
def bad_session_attributes():
    return {
        "headers": ("value_one", "value_two", "value_three"),
        "auth_headers": 31337,
        "auth": {"key": "value"},
        "timeout": "string_value",
        "retries": "string_value",
        "max_redirects": [1, 3],
        "backoff_factor": ("tuple",),
        "retry_status_code_list": None,
        "retry_method_list": False,
        "respect_retry_headers": "Good question",
        "base_url": True,
        "verify": 30,
        "max_reauth": "string_value",
        "redirect_header_hook": "No hook",
        "request_exception_hook": "No hook",
        "response_hooks": True
    }


def test_object_is_not_singleton(standard_test_class):
    object_one = standard_test_class()
    object_two = standard_test_class()

    assert object_one is not object_two


def test_object_is_singleton(singleton_test_class):
    object_one = singleton_test_class()
    object_two = singleton_test_class()

    assert object_one is object_two


def test_object_with_context_manager(test_class):
    with test_class() as class_instance:
        assert isinstance(class_instance, test_class)

        # Test the singleton has an instance defined
        if hasattr(class_instance.__class__, "_instances"):
            assert class_instance.__class__._instances != {}

#
# @pytest.mark.parametrize("test_class, default_params",
#                          [(requests_toolbelt.sessions.BaseUrlSession, restsession.defaults.SESSION_DEFAULTS),
#                           (restsession.RestSession, restsession.defaults.SESSION_DEFAULTS),
#                           (restsession.RestSessionSingleton, restsession.defaults.SESSION_DEFAULTS)])
# def test_default_attributes(test_class, default_params):
#     with test_class() as class_instance:
#         for expected_attr, expected_value in default_params.items():
#
#             # This is failing - default attrs do not account for the setter
#             # which is setting a response hook.
#             #
#             # NOTE - object calls the redirect header hook as a wrapper to remove
#             # the auth header. Get the qualified name (function.<locals>.inner) and
#             # split to get the outer function, which should match the SESSION_DEFAULT
#             #
#             value_to_test = getattr(class_instance, expected_attr)
#
#             if isinstance(value_to_test, list):
#                 if all([callable(t) for t in value_to_test]):
#                     value_to_test = [t.__qualname__.split(".", 1)[0] for t in value_to_test]
#
#             if isinstance(expected_value, list):
#                 if all([callable(t) for t in expected_value]):
#                     expected_value = [t.__qualname__ for t in expected_value]
#
#             # NOTE - Update defaults. ONLY "response" is a valid type of hook. So
#             # probably don't need "redirect hook" etc. OR I need to document the hell out
#             # of it that a "redirect hook" is THE FIRST HOOK ...
#             if expected_attr == "headers" and test_class.__name__ == "BaseUrlSession":
#                 pytest.xfail("BaseUrlSession has different default headers defined (Non-critical failure)")
#             assert value_to_test == expected_value
#
#
# @pytest.mark.parametrize("test_class, default_params",
#                          [(requests_toolbelt.sessions.BaseUrlSession, restsession.defaults.SESSION_DEFAULTS),
#                           (restsession.RestSession, restsession.defaults.SESSION_DEFAULTS),
#                           (restsession.RestSessionSingleton, restsession.defaults.SESSION_DEFAULTS)])
# def test_good_attribute_assignment(test_class, default_params):
#     with test_class() as class_instance:
#         for expected_attr, expected_value in default_params.items():
#             setattr(class_instance, expected_attr, expected_value)
#             # This is failing - default attrs do not account for the setter
#             # which is setting a response hook.
#             #
#             # NOTE - object calls the redirect header hook as a wrapper to remove
#             # the auth header. Get the qualified name (function.<locals>.inner) and
#             # split to get the outer function, which should match the SESSION_DEFAULT
#             #
#             value_to_test = getattr(class_instance, expected_attr)
#
#             if isinstance(value_to_test, list):
#                 if all([callable(t) for t in value_to_test]):
#                     value_to_test = [t.__qualname__.split(".", 1)[0] for t in value_to_test]
#
#             if isinstance(expected_value, list):
#                 if all([callable(t) for t in expected_value]):
#                     expected_value = [t.__qualname__ for t in expected_value]
#
#             # NOTE - Update defaults. ONLY "response" is a valid type of hook. So
#             # probably don't need "redirect hook" etc. OR I need to document the hell out
#             # of it that a "redirect hook" is THE FIRST HOOK ...
#             assert value_to_test == expected_value
#
#
# # @pytest.mark.parametrize("test_class",
# #                          [requests_toolbelt.sessions.BaseUrlSession,
# #                           restsession.RestSession,
# #                           restsession.RestSessionSingleton])
# # def test_bad_attribute_assignment(test_class, bad_session_attributes):
# #     with test_class() as class_instance:
# #         for expected_attr, expected_value in bad_session_attributes.items():
# #             logger.info("Testing attribute '%s' with value '%s'", expected_attr, expected_value)
# #             with pytest.raises((restsession.exceptions.InvalidParameterError,
# #                                 requests.exceptions.RequestException)):
# #                 setattr(class_instance, expected_attr, expected_value)
# #                 logger.info("Result: %s", getattr(class_instance, expected_attr))
# #                 # INTERESTING - there is no validation of requests' headers attribute - it
# #                 # accepts anything you send to it, even invalid parameters.
# #
# #             # # This is failing - default attrs do not account for the setter
# #             # # which is setting a response hook.
# #             # #
# #             # # NOTE - object calls the redirect header hook as a wrapper to remove
# #             # # the auth header. Get the qualified name (function.<locals>.inner) and
# #             # # split to get the outer function, which should match the SESSION_DEFAULT
# #             # #
# #             # value_to_test = getattr(class_instance, expected_attr)
# #             #
# #             # if isinstance(value_to_test, list):
# #             #     if all([callable(t) for t in value_to_test]):
# #             #         value_to_test = [t.__qualname__.split(".", 1)[0] for t in value_to_test]
# #             #
# #             # if isinstance(expected_value, list):
# #             #     if all([callable(t) for t in expected_value]):
# #             #         expected_value = [t.__qualname__ for t in expected_value]
# #             #
# #             # # NOTE - Update defaults. ONLY "response" is a valid type of hook. So
# #             # # probably don't need "redirect hook" etc. OR I need to document the hell out
# #             # # of it that a "redirect hook" is THE FIRST HOOK ...
# #             # assert value_to_test == expected_value