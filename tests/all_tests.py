"""
Combine all tests into a single file - this will generate a consolidated
log at the end.

When tests are called one-by-one, a separate section is created in the
logs.
"""

from test_requests import TestBasicRequests
from test_retries import TestRequestRetries
from test_redirects import TestRequestRedirects
from test_authorization import TestRequestAuthorization
from pyats import aetest
import logging
import sys

logger = logging.getLogger(__name__)


def get_class(path, class_name):
    logger.info(sys.modules[path])
    return getattr(sys.modules[path], class_name)


class LocalSetup(aetest.Testcase):
    @aetest.setup
    def loop_marker(self, test_classes):
        # To prevent classes from being passed as callables, get the class
        # from a string. Tests can then be sure that a new object is created
        # by using self.parameters["test_class"]()
        all_classes = [get_class("restsession", class_name) for class_name in test_classes]

        # # Mark each test for looping
        aetest.loop.mark(basic_requests, test_class=all_classes)
        aetest.loop.mark(request_retries, test_class=all_classes)
        aetest.loop.mark(request_redirect, test_class=all_classes)
        aetest.loop.mark(request_auth, test_class=all_classes)


class basic_requests(TestBasicRequests):
    ...


class request_retries(TestRequestRetries):
    ...


class request_redirect(TestRequestRedirects):
    ...


class request_auth(TestRequestAuthorization):
    ...
