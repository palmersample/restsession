import logging
from BaseHttpServer import BaseHttpServer
from pyats import aetest
from restsession import HttpSessionClass, HttpSessionSingletonClass
from requests.exceptions import TooManyRedirects
from http.server import BaseHTTPRequestHandler
import re

logger = logging.getLogger(__name__)


class TestRequestRedirects(BaseHttpServer):

    @aetest.test
    def test_too_many_redirects(self, url_path, request_redirect_count):
        class MockServerRequestHandler(BaseHTTPRequestHandler):
            server_address = None
            request_count = 0
            redirect_count = 0

            def do_GET(self):
                if re.match(f"/{url_path}", self.path):
                    self.__class__.request_count += 1
                    self.__class__.redirect_count += 1

                    next_server = f"http://{self.__class__.server_address}/{url_path}"

                    self.send_response(301)
                    self.send_header(
                        "Content-Type", "application/json; charset=utf-8"
                    )
                    self.send_header("Location", next_server)
                    self.end_headers()
                return

        test_server = self.start_mock_server(MockServerRequestHandler)
        test_url = f"http://{MockServerRequestHandler.server_address}/{url_path}"

        # Expected redirect should be the configured retry count + 1, as the
        # first request hits and then receives a 301. After experiencing
        # (request_redirect_count) responses of 301, the exception will be raised.
        # Each request hitting the server will increment the redirect counter
        expected_redirect_count = request_redirect_count + 1

        test_class = self.parameters["test_class"]

        if hasattr(test_class, "_instances"):
            test_class._instances = {}

        test_instance = test_class(max_redirect=request_redirect_count)

        try:
            test_instance.get(test_url)
        except TooManyRedirects:
            logger.info("Caught expected TooManyRedirect exception.")
            # pass
            # self.passed()
        except Exception as err:
            self.failed(f"Unexpected exception was raised:\n{err}")
        finally:
            self.stop_mock_server(test_server)

        assert MockServerRequestHandler.redirect_count == expected_redirect_count, \
            f"Expected {expected_redirect_count} redirects, " \
            f"server received {MockServerRequestHandler.redirect_count}"


    @aetest.test
    def test_max_redirects(self, url_path, request_redirect_count):
        class MockServerRequestHandler(BaseHTTPRequestHandler):
            server_address = None
            request_count = 0
            redirect_count = 0

            def do_GET(self):
                if re.match(f"/{url_path}", self.path):
                    if self.__class__.request_count < expected_redirect_count:
                        self.__class__.request_count += 1
                        self.__class__.redirect_count += 1

                        next_server = f"http://{self.__class__.server_address}/{url_path}"

                        self.send_response(301)
                        self.send_header(
                            "Content-Type", "application/json; charset=utf-8"
                        )
                        self.send_header("Location", next_server)
                    else:
                        self.__class__.request_count += 1
                        self.send_response(200)
                    self.end_headers()
                return

        test_server = self.start_mock_server(MockServerRequestHandler)
        test_url = f"http://{MockServerRequestHandler.server_address}/{url_path}"

        expected_redirect_count = request_redirect_count
        expected_request_count = request_redirect_count + 1

        test_class = self.parameters["test_class"]

        if hasattr(test_class, "_instances"):
            test_class._instances = {}

        test_instance = test_class(max_redirect=request_redirect_count)

        try:
            test_instance.get(test_url)
        except Exception as err:
            self.failed(f"Unexpected exception was raised:\n{err}")
        finally:
            self.stop_mock_server(test_server)

        assert MockServerRequestHandler.request_count == expected_request_count, \
            f"Expected {expected_request_count} requests, " \
            f"server received {MockServerRequestHandler.request_count}"
        assert MockServerRequestHandler.redirect_count == expected_redirect_count, \
            f"Expected {expected_redirect_count} redirects, " \
            f"server received {MockServerRequestHandler.redirect_count}"
