import logging
from BaseHttpServer import BaseHttpServer
from pyats import aetest
# from restsession import HttpSessionClass, HttpSessionSingletonClass
from requests.exceptions import RetryError
from http.server import BaseHTTPRequestHandler
import re
import time

logger = logging.getLogger(__name__)


class TestRequestRetries(BaseHttpServer):

    @aetest.test
    def test_too_many_respectful_retries(self, url_path, request_retry_count):

        class MockServerRequestHandler(BaseHTTPRequestHandler):
            server_address = None
            request_count = 0
            retry_count = 0

            def do_GET(self):
                if re.match(f"/{url_path}", self.path):
                    self.__class__.request_count += 1
                    self.__class__.retry_count += 1

                    self.send_response(429)
                    self.send_header(
                        "Content-Type", "application/json; charset=utf-8"
                    )
                    self.send_header("Retry-After", "1")
                    self.end_headers()
                return

        test_server = self.start_mock_server(MockServerRequestHandler)
        test_url = f"http://{MockServerRequestHandler.server_address}/{url_path}"

        # Expected retry should be the configured retry count + 1, as the
        # first request hits and then receives a 429. After experiencing
        # (request_retry_count) responses of 429, the exception will be raised.
        # Each request hitting the server will increment the retry counter
        expected_retry_count = request_retry_count + 1

        test_class = self.parameters["test_class"]

        if hasattr(test_class, "_instances"):
            test_class._instances = {}

        test_instance = test_class(retries=request_retry_count)

        try:
            start_time = time.time()
            test_instance.get(test_url)
        except RetryError:
            end_time = time.time() - start_time
            # self.passed()
        except Exception as err:
            self.failed(f"Unexpected exception was raised:\n{err}")
        finally:
            self.stop_mock_server(test_server)

        assert MockServerRequestHandler.retry_count == expected_retry_count, \
            f"Expected {expected_retry_count} retries, " \
            f"server received {MockServerRequestHandler.retry_count}"

        logger.info("Total time for request: %s", end_time)

        assert end_time >= request_retry_count, \
            "Total time of requests should be larger than the request retry Count.\n" \
            f"Number of retries: {MockServerRequestHandler.retry_count}\n" \
            f"Elapsed time: {end_time}"

        assert MockServerRequestHandler.retry_count == expected_retry_count, \
            f"Expected {expected_retry_count} retries, " \
            f"server received {MockServerRequestHandler.retry_count}"

    @aetest.test
    def test_too_many_disrespectful_retries(self, url_path, request_retry_count):

        class MockServerRequestHandler(BaseHTTPRequestHandler):
            server_address = None
            request_count = 0
            retry_count = 0

            def do_GET(self):
                if re.match(f"/{url_path}", self.path):
                    self.__class__.request_count += 1
                    self.__class__.retry_count += 1

                    self.send_response(429)
                    self.send_header(
                        "Content-Type", "application/json; charset=utf-8"
                    )
                    self.send_header("Retry-After", "1")
                    self.end_headers()
                return

        test_server = self.start_mock_server(MockServerRequestHandler)
        test_url = f"http://{MockServerRequestHandler.server_address}/{url_path}"

        # Expected retry should be the configured retry count + 1, as the
        # first request hits and then receives a 429. After experiencing
        # (request_retry_count) responses of 429, the exception will be raised.
        # Each request hitting the server will increment the retry counter
        expected_retry_count = request_retry_count + 1

        test_class = self.parameters["test_class"]

        if hasattr(test_class, "_instances"):
            test_class._instances = {}

        test_instance = test_class(retries=request_retry_count,
                                   respect_retry_headers=False)

        try:
            start_time = time.time()
            test_instance.get(test_url)
        except RetryError:
            end_time = time.time() - start_time
        except Exception as err:
            self.failed(f"Unexpected exception was raised:\n{err}")
        finally:
            self.stop_mock_server(test_server)

        assert MockServerRequestHandler.retry_count == expected_retry_count, \
            f"Expected {expected_retry_count} retries, " \
            f"server received {MockServerRequestHandler.retry_count}"

        logger.info("Total time for request: %s", end_time)

        assert end_time < request_retry_count, \
            "Total time of requests should be less than the request retry Count.\n" \
            f"Number of retries: {MockServerRequestHandler.retry_count}\n" \
            f"Elapsed time: {end_time}"

        assert MockServerRequestHandler.retry_count == expected_retry_count, \
            f"Expected {expected_retry_count} retries, " \
            f"server received {MockServerRequestHandler.retry_count}"

    @aetest.test
    def test_max_retries(self, url_path, request_retry_count):
        class MockServerRequestHandler(BaseHTTPRequestHandler):
            server_address = None
            request_count = 0
            retry_count = 0

            def do_GET(self):
                if re.match(f"/{url_path}", self.path):
                    if self.__class__.request_count < expected_retry_count:
                        self.__class__.request_count += 1
                        self.__class__.retry_count += 1

                        self.send_response(429)
                        self.send_header(
                            "Content-Type", "application/json; charset=utf-8"
                        )
                        self.send_header("Retry-After", "1")
                    else:
                        self.__class__.request_count += 1
                        self.send_response(200)
                    self.end_headers()
                return

        test_server = self.start_mock_server(MockServerRequestHandler)
        test_url = f"http://{MockServerRequestHandler.server_address}/{url_path}"

        # Expected retry should be the configured retry count + 1, as the
        # first request hits and then receives a 429. After experiencing
        # (request_retry_count) responses of 429, the exception will be raised.
        # Each request hitting the server will increment the retry counter
        expected_retry_count = request_retry_count
        expected_request_count = request_retry_count + 1

        test_class = self.parameters["test_class"]

        if hasattr(test_class, "_instances"):
            test_class._instances = {}

        test_instance = test_class(retries=request_retry_count)

        try:
            test_instance.get(test_url)
        except Exception as err:
            self.failed(f"Unexpected exception was raised:\n{err}")
        finally:
            self.stop_mock_server(test_server)

        assert MockServerRequestHandler.retry_count == expected_retry_count, \
            f"Expected {expected_retry_count} retries, " \
            f"server received {MockServerRequestHandler.retry_count}"
        assert MockServerRequestHandler.request_count == expected_request_count, \
            f"Expected {expected_request_count} request, " \
            f"server received {MockServerRequestHandler.request_count}"

# Need tests for:
# retry_status_code_list: list[int] = SESSION_DEFAULTS["retry_status_codes"],
#                 retry_method_list: list[str] = SESSION_DEFAULTS["retry_methods"],
#                 respect_retry_headers:
