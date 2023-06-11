import logging
from requests.exceptions import MissingSchema, TooManyRedirects, RetryError, HTTPError
from pyats import aetest
from http.server import BaseHTTPRequestHandler, HTTPServer
import socket
from threading import Thread
import sys
import re
from urllib3.exceptions import MaxRetryError
from pathlib import Path # if you haven't already done so

file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from restsession import HttpSessionClass, HttpSessionSingletonClass

logger = logging.getLogger(__name__)

normal_class: None
singleton_class: None


class MockServerRequestHandler(BaseHTTPRequestHandler):
    max_redirect = 0
    max_retries = 0
    request_count = 0
    redirect_count = 0
    retry_count = 0
    server_port = None
    second_port = None

    def do_GET(self):
        logger.info("\nHTTP SERVER: GET REQUEST RECEIVED\nPath: %s", self.path)
        logger.info("HTTP SERVER: Request headers received:\n%s", self.headers)

        # self.redirect_count = 0

        # test_url = re.compile(r"/test-url")
        if re.match(r"/base-url-test", self.path):
            MockServerRequestHandler.request_count += 1
            self.send_response(200)

        elif re.match(r"/limited-redirect", self.path):
            if MockServerRequestHandler.request_count < MockServerRequestHandler.max_redirect:
                MockServerRequestHandler.request_count += 1
                MockServerRequestHandler.redirect_count += 1
                logger.info("HTTP SERVER: Sending HTTP 301 redirect to: %s\n", self.path)
                self.send_response(301)
                self.send_header("Location", self.path)
            else:
                MockServerRequestHandler.request_count += 1

                logger.info("Sending HTTP 200 SUCCESS\n")
                self.send_response(200)

        elif re.match(r"/infinite-redirect", self.path):
            # Increment request count for each redirect
            MockServerRequestHandler.request_count += 1
            MockServerRequestHandler.redirect_count += 1
            next_server = f"http://192.168.64.52:{MockServerRequestHandler.second_port}/infinite-redirect"
            logger.info("HTTP SERVER: Sending HTTP 301 redirect to: %s\n", next_server)
            # logger.info("HTTP SERVER: Sending HTTP 301 redirect to: %s\n", self.path)
            self.send_response(301)
            # self.send_header(f"Location", self.path)
            # self.send_header("Location", f"http://127.0.0.1:{MockServerRequestHandler.server_port}")
            self.send_header("Location", next_server)

        elif re.match(r"/limited-retry-after", self.path):
            if MockServerRequestHandler.request_count < MockServerRequestHandler.max_retries:
                # Only increment request count for a 429 response
                MockServerRequestHandler.request_count += 1
                MockServerRequestHandler.retry_count += 1
                logger.info("HTTP SERVER: Sending HTTP 429 Retry-After: 1 second\n")
                self.send_response(429)
                self.send_header("Retry-After", "1")
            else:
                MockServerRequestHandler.request_count += 1
                logger.info("HTTP SERVER: Sending HTTP 200 SUCCESS\n")
                self.send_response(200)

        elif re.match(r"/infinite-retry-after", self.path):
            # Increment the counter on every 429
            MockServerRequestHandler.request_count += 1
            MockServerRequestHandler.retry_count += 1
            logger.info("HTTP SERVER: Sending HTTP 429 Retry-After: 1 second\n")
            self.send_response(429)
            self.send_header("Retry-After", "1")

        self.end_headers()
        logger.info("HTTP SERVER: Total requests received: %s", MockServerRequestHandler.request_count)
        logger.info("HTTP SERVER: Total redirects issued: %s", MockServerRequestHandler.redirect_count)
        logger.info("HTTP SERVER: Total retry responses issued: %s\n", MockServerRequestHandler.retry_count)

        return


def get_free_port(bind_address=None):
    s = socket.socket(socket.AF_INET, type=socket.SOCK_STREAM)
    s.bind((bind_address or 'localhost', 0))
    address, port = s.getsockname()
    s.close()
    return port


def reset_server_counters(all=False, redirect=False, retry=False):
    if all:
        MockServerRequestHandler.request_count = 0
        MockServerRequestHandler.redirect_count = 0
        MockServerRequestHandler.retry_count = 0
    elif redirect:
        MockServerRequestHandler.redirect_count = 0
    elif retry:
        MockServerRequestHandler.retry_count = 0


class TestMockServer:
    @classmethod
    def setup_class(cls):
        # Configure mock server.
        cls.mock_server_port = get_free_port()
        cls.mock_server = HTTPServer(('localhost', cls.mock_server_port), MockServerRequestHandler)

        # Start running mock server in a separate thread.
        # Daemon threads automatically shut down when the main process exits.
        cls.mock_server_thread = Thread(target=cls.mock_server.serve_forever)
        cls.mock_server_thread.daemon = True
        cls.mock_server_thread.start()


def start_mock_server(bind_address, port):
    mock_server = HTTPServer((bind_address or 'localhost', port), MockServerRequestHandler)
    mock_server_thread = Thread(target=mock_server.serve_forever)
    mock_server_thread.daemon = True
    mock_server_thread.start()


# class HttpServerSetup(aetest.CommonSetup):
#
#     @aetest.subsection
#     def start_webserver(self):
#         webserver_port = get_free_port()
#         start_mock_server(webserver_port)
#         self.parameters['webserver_port'] = webserver_port
#     #
#     @aetest.subsection
#     def set_params(self):
#         self.parameters["normal_class"] = HttpSessionClass
#         self.parameters["singleton_class"] = HttpSessionSingletonClass

def get_class(path, class_name):
    logger.info(sys.modules[path])
    return getattr(sys.modules[path], class_name)


class CommonSetup(aetest.CommonSetup):
    @aetest.subsection
    def set_class_from_string(self):
        globals()["normal_class"] = get_class("src", normal_class)
        globals()["singleton_class"] = get_class("src", singleton_class)

    @aetest.subsection
    def mark_tests_for_looping(self):
        aetest.loop.mark(TestRequests, test_class=[normal_class,
                                                   singleton_class]
                         )


class TestRequests(aetest.Testcase):
    @aetest.setup
    def prepare(self):
        """
        Start the http.server instance to respond to requests

        :return: None
        """
        webserver_host_one = "127.0.0.1"
        webserver_port_one = get_free_port(webserver_host_one)
        webserver_url = f"http://{webserver_host_one}:{webserver_port_one}"
        start_mock_server(webserver_host_one, webserver_port_one)

        webserver_host_two = "192.168.64.52"
        webserver_port_two = get_free_port(webserver_host_two)
        # webserver_url_two = f"http://{webserver_host_two}:{webserver_port_two}"
        start_mock_server(webserver_host_two, webserver_port_two)

        self.parameters["webserver_port"] = webserver_port_one

        self.parameters["webserver_url"] = webserver_url
        MockServerRequestHandler.server_port = webserver_port_one
        MockServerRequestHandler.second_port = webserver_port_two


    @aetest.test
    def test_basic_get(self, steps, webserver_url):
        """
        Test that a request to an incomplete URL (e.g. missing base URL) raises
        a "MissingSchema" exception

        :return: None
        """
        test_class = self.parameters["test_class"]
        if hasattr(test_class, "_instances"):
            test_class._instances = {}

        request_session = test_class()
        base_url = f"{webserver_url}/"
        relative_url = "base-url-test"
        explicit_url = f"{base_url}{relative_url}"

        with steps.start("Negative testing - exception should be raised", continue_=True) as step:
            reset_server_counters(all=True)
            try:
                logger.info("Sending GET request to relative URL: %s", relative_url)
                request_session.get(url=relative_url)
            except MissingSchema as err:
                logger.error("OK : Expected exception 'MissingSchema' was raised. Details:\n%s", err)
                step.passed(f"Invalid URL provided - caught MissingSchema exception")
            else:
                step.failed("Invalid URL provided and no exception raised")

        with steps.start("Positive testing with explicit (non-base) URL -  no exception should be raised") as step:
            reset_server_counters(all=True)
            response = None
            try:
                logger.info("The request session base URL is: %s", request_session.base_url)
                logger.info("Sending GET request to explicit URL: %s", explicit_url)
                response = request_session.get(url=explicit_url)

            except Exception as err:
                step.failed(f"An unexpected exception was raised during testing:\n{err}")
            else:
                try:
                    assert response.ok, "No exception raised BUT the response was a non-OK status code"
                except AssertionError as err:
                    step.failed(err)
                else:
                    step.passed(f"No exception was raised and the server returned status {response.status_code}")

        with steps.start("Positive testing with base URL - no exception should be raised") as step:
            reset_server_counters(all=True)
            response = None
            try:
                request_session.base_url = base_url
                logger.info("The request session base URL is: %s", request_session.base_url)
                logger.info("Sending GET request to relative URL: %s", relative_url)
                response = request_session.get(url=relative_url)
            except Exception as err:
                step.failed(f"An unexpected exception was raised during testing:\n{err}")
            else:
                try:
                    assert response.ok, "No exception raised BUT the response was a non-OK status code"
                except AssertionError as err:
                    step.failed(err)
                else:
                    step.passed(f"No exception was raised and the server returned status {response.status_code}")

    @aetest.test
    def test_too_many_redirects(self, steps, webserver_url):
        """
        Test that too many redirects from the server causes TooManyRedirects to
        be raised

        The request count from the server will be (max_redirect + 1) on failure.

        For example, max_redirect set to 3 will result in the following failure:

        Request 1 (301): Initial request results in redirect #1 (request count = 1)
        Request 2 (301): Second request results in redirect #2 (request count = 2)
        Request 3 (301): Third request results in redirect #3 (request count = 3)
        Request 4 (301): Fourth request results in exceeding max redirect (request count = 4)

        But the following flow will result in success:

        Request 1 (301): Initial request results in redirect #1 (request count = 1)
        Request 2 (301): Second request results in redirect #2 (request count = 2)
        Request 3 (301): Third request results in redirect #3 (request count = 3)
        Request 4 (200): Fourth request is a success, max redirect not exceeded (request count = 4)


        :param steps: pyATS Steps object
        :param webserver_port:
        :return:
        """
        test_class = self.parameters["test_class"]
        if hasattr(test_class, "_instances"):
            test_class._instances = {}

        base_url = f"{webserver_url}/"

        max_redirect = 3
        too_many_redirect_count = max_redirect + 1

        failure_url = "infinite-redirect"
        success_url = "limited-redirect"

        logger.info("Setting base URL to %s", base_url)
        request_session = test_class(base_url=base_url, max_redirect=max_redirect, username="nobody", password="Nopassword")
        logger.info("Session created with max redirect: %s",
                    request_session.max_redirect)
        logger.info("Session base URL: %s", request_session.base_url)

        # Set the max redirect count for the MockServerRequestHandler class
        MockServerRequestHandler.max_redirect = max_redirect

        for mounted_adapter in request_session.http.adapters:
            logger.info("Number of redirects for adapter '%s': %s", mounted_adapter,
                        request_session.http.get_adapter(mounted_adapter).max_retries.redirect)

        with steps.start("Negative testing - exception should be raised", continue_=True) as step:
            # Reset the MockServerRequestHandler's request count
            reset_server_counters(all=True)
            response = None
            try:
                # request_session.http.headers.update({"Authorization": "Basic 12345asdf"})
                response = request_session.get(url=failure_url)
            except TooManyRedirects as err:
            # except RetryError as err:
                logger.error("OK : Expected exception 'RetryError' was raised. Details:\n%s", err)
                logger.info("Number of requests received by the server: %s", MockServerRequestHandler.request_count)
                logger.info("Number of redirects returned by the server: %s", MockServerRequestHandler.redirect_count)

                try:
                    assert MockServerRequestHandler.redirect_count == too_many_redirect_count, \
                        f"The redirect count did not match the expected failure threshold."
                except AssertionError as err:
                    step.failed("TooManyRedirects raised but the redirect count did not match the "
                                f"expected failure limit:\n{err}")
                else:
                    step.passed(f"Max redirect count is {max_redirect}, "
                                f"received {MockServerRequestHandler.redirect_count}")
            else:
                step.failed(f"No exception raised after redirect limit:\n"
                            f"Expected {too_many_redirect_count} but the redirect "
                            f"count was {MockServerRequestHandler.redirect_count}.\n"
                            f"The last status code returned was: {response.status_code}")

        with steps.start("Positive testing - no exception should be raised.") as step:
            reset_server_counters(all=True)
            response = None
            try:
                response = request_session.get(url=success_url)
            except TooManyRedirects as err:
                logger.info("Number of requests received by the server: %s", MockServerRequestHandler.request_count)
                logger.info("Number of redirects returned by the server: %s", MockServerRequestHandler.redirect_count)

                step.failed(f"TooManyRedirects was raised after {MockServerRequestHandler.redirect_count} "
                            f"redirects.\nMax redirect set to {max_redirect} and the success criteria "
                            f"was <= {max_redirect} redirects.")
            else:
                logger.info("Number of requests received by the server: %s", MockServerRequestHandler.request_count)
                logger.info("Number of redirects returned by the server: %s", MockServerRequestHandler.redirect_count)

                try:
                    assert MockServerRequestHandler.redirect_count <= max_redirect, \
                        f"The redirect count was NOT less or equal to the expected threshold of {max_redirect}."
                except AssertionError as err:
                    step.failed(f"No exception raised the redirect count assertion failed:\n{err}")
                else:
                    step.passed(f"No redirect exception caught, total request count was: "
                                f"{MockServerRequestHandler.request_count}\n"
                                f"Number of redirects: {MockServerRequestHandler.redirect_count}\n"
                                f"Max redirects tolerated: {max_redirect}")

    @aetest.test
    def test_too_many_retries(self, steps, webserver_url):
        test_class = self.parameters["test_class"]
        if hasattr(test_class, "_instances"):
            test_class._instances = {}

        base_url = f"{webserver_url}/"

        max_retries = 3
        too_many_retries_count = max_retries + 1

        failure_url = "infinite-retry-after"
        success_url = "limited-retry-after"

        request_session = test_class(base_url=base_url, retries=max_retries)
        logger.info("Session created with max retries: %s",
                    request_session.retries)
        logger.info("Session base URL: %s", request_session.base_url)

        # Set the max redirect count for the MockServerRequestHandler class
        MockServerRequestHandler.max_retries = max_retries


        with steps.start("Negative testing - exception should be raised", continue_=True) as step:
            # Reset the MockServerRequestHandler's request count
            reset_server_counters(all=True)
            response = None
            try:
                response = request_session.get(url=failure_url)
            except RetryError as err:
                logger.error("OK : Expected exception 'RetryError' was raised. Details:\n%s", err)
                logger.info("Number of requests received by the server: %s", MockServerRequestHandler.request_count)
                logger.info("Number of retries returned by the server: %s", MockServerRequestHandler.retry_count)

                try:
                    assert MockServerRequestHandler.retry_count == too_many_retries_count, \
                        f"The retry count did not match the expected failure threshold."
                except AssertionError as err:
                    step.failed("RetryError raised but the retry count did not match the "
                                f"expected failure limit:\n{err}")
                else:
                    step.passed(f"Max retry count is {max_retries}, "
                                f"received {MockServerRequestHandler.retry_count}")
            else:
                step.failed(f"No exception raised after retry limit:\n"
                            f"Expected {too_many_retries_count} but the retry "
                            f"count was {MockServerRequestHandler.retry_count}.\n"
                            f"The last status code returned was: {response.status_code}")

        with steps.start("Positive testing - no exception should be raised.") as step:
            reset_server_counters(all=True)
            response = None
            try:
                response = request_session.get(url=success_url)
            except RetryError as err:
                logger.info("Number of requests received by the server: %s", MockServerRequestHandler.request_count)
                logger.info("Number of retries returned by the server: %s", MockServerRequestHandler.retry_count)

                step.failed(f"RetryError was raised after {MockServerRequestHandler.retry_count} "
                            f"retries.\nMax retry set to {max_retries} and the success criteria "
                            f"was <= {max_retries} retries.")
            else:
                logger.info("Number of requests received by the server: %s", MockServerRequestHandler.request_count)
                logger.info("Number of retries returned by the server: %s", MockServerRequestHandler.retry_count)

                try:
                    assert MockServerRequestHandler.retry_count <= max_retries, \
                        f"The retry count was NOT less or equal to the expected threshold of {max_retries}."
                except AssertionError as err:
                    step.failed(f"No exception raised the retry count assertion failed:\n{err}")
                else:
                    step.passed(f"No RetryError exception caught, total request count was: "
                                f"{MockServerRequestHandler.request_count}\n"
                                f"Number of retries: {MockServerRequestHandler.retry_count}\n"
                                f"Max retries tolerated: {max_retries}")

    @aetest.test
    def find_a_way_to_test_different_server_name_and_see_if_auth_header_removed_on_redirect(self):
        """
        Check the method name. Authorization header MUST be removed on redirect when going
        to another host.

        And add a test that preserves the header when going to the same host. Have observed
        this behavior using NetCat and saw no Auth header, but it ALWAYS shows up on the
        mock server's logger() statements...
        :return:
        """
        assert False

    @aetest.test
    def figure_out_how_to_time_each_test_like_retry_after_headers(self):
        """
        Nested methods with decorators? Time each call via callable function?
        :return:
        """
        assert False

    @aetest.test
    def test_other_verbs_like_post_put_for_payload(self):
        assert False

    @aetest.test
    def test_redirect_and_retry_header_combo(self):
        """
        Need to identify a good method to time request intervals for, say,
        1 second.

        Also need to do this test for the backoff_interval according to the
        formula for enough requests to take the time up to, say, 1 second.
        :return:
        """
        assert False

    @aetest.test
    def test_backoff_interval(self):
        assert False
