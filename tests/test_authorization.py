"""

TESTS NEEDED:


Use the "remove header on redirect" to remove the custom X-Auth-Token header
generated in the custom auth module - IMPORTANT TO PREVENT MITM / TOKEN HIJACK
E.G. proxy in the middle with same name / hijack / whatever

SO - to double-check, check that TLS will re-verify a new server on redirect!
    load a TRUSTED cert for first request, do a redirect to INVALID site to
    test the TLS is checked on every request and not just to first server. Would
    be good to share with the community or improve the project.

ALSO - find a way to check the token expiration and call a renewal

ALSO - create a custom handler class that does NOTHING but has a class variable
    to use as an accumulator. Each element of the list is the time between
    request (start_time - time.time()). TEST THE BACKOFF PERIOD. Set backoff
    to something readable like 1 or 2 seconds, calculate (x retries) and pull
    the class list to see that request 1 was 2 seconds, request 2 was 2.38 (EXAMPLE)
    seconds, that it incrementally increases and is >= expected time. NOT LESS THAN

    Because the hook and class with the var are defined HERE, the HttpSession*Class
    will load it all and the callback function will just increment the class var
    each time it's called on a retry along with adding the time diff for each interval.



"""
import logging
from BaseHttpServer import BaseHttpServer
from pyats import aetest
import requests
from http.server import BaseHTTPRequestHandler
import base64
import re
import json

logger = logging.getLogger(__name__)


class TestRequestAuthorization(BaseHttpServer):

    @aetest.test
    def test_basic_auth(self, url_path, basic_auth_username, basic_auth_password):
        class MockServerRequestHandler(BaseHTTPRequestHandler):
            server_address = None
            request_count = 0
            received_auth = None

            def do_GET(self):
                if re.match(f"/{url_path}", self.path):
                    self.__class__.request_count += 1

                    self.__class__.received_auth = self.headers.get("Authorization", None)
                    self.send_response(200)
                    self.send_header(
                        "Content-Type", "application/json; charset=utf-8"
                    )
                    self.end_headers()
                return

        test_server = self.start_mock_server(MockServerRequestHandler)
        test_url = f"http://{MockServerRequestHandler.server_address}/{url_path}"

        expected_request_count = 1

        authorization_string = f"{basic_auth_username}:{basic_auth_password}"
        base64_auth = base64.b64encode(bytes(authorization_string, 'utf-8')).decode('utf-8')
        expected_auth_value = f"Basic {base64_auth}"

        test_class = self.parameters["test_class"]

        if hasattr(test_class, "_instances"):
            test_class._instances = {}

        test_instance = test_class(username=basic_auth_username,
                                   password=basic_auth_password)

        try:
            test_instance.get(test_url)
        except Exception as err:
            self.failed(f"Unexpected exception was raised:\n{err}")
        finally:
            self.stop_mock_server(test_server)

        assert MockServerRequestHandler.received_auth == expected_auth_value, \
            f"Expected auth header '{expected_auth_value}', " \
            f"server received {MockServerRequestHandler.received_auth}"
        assert MockServerRequestHandler.request_count == expected_request_count, \
            f"Expected {expected_request_count} requests, " \
            f"server received {MockServerRequestHandler.request_count}"

    @aetest.test
    def test_manual_basic_auth(self, url_path, basic_auth_username, basic_auth_password):
        class MockServerRequestHandler(BaseHTTPRequestHandler):
            server_address = None
            request_count = 0
            received_auth = None

            def do_GET(self):
                if re.match(f"/{url_path}", self.path):
                    self.__class__.request_count += 1

                    self.__class__.received_auth = self.headers.get("Authorization", None)
                    self.send_response(200)
                    self.send_header(
                        "Content-Type", "application/json; charset=utf-8"
                    )
                    self.end_headers()
                return

        test_server = self.start_mock_server(MockServerRequestHandler)
        test_url = f"http://{MockServerRequestHandler.server_address}/{url_path}"
        expected_request_count = 1

        authorization_string = f"{basic_auth_username}:{basic_auth_password}"
        base64_auth = base64.b64encode(bytes(authorization_string, 'utf-8')).decode('utf-8')
        expected_auth_value = f"Basic {base64_auth}"

        test_class = self.parameters["test_class"]

        if hasattr(test_class, "_instances"):
            test_class._instances = {}

        test_instance = test_class()
        test_instance.auth = (basic_auth_username, basic_auth_password)

        try:
            test_instance.get(test_url)
        except Exception as err:
            self.failed(f"Unexpected exception was raised:\n{err}")
        finally:
            self.stop_mock_server(test_server)

        assert test_instance.username == basic_auth_username, \
            "Username attribute does not match auth tuple." \
            f"Expected: '{basic_auth_username}', configured is '{test_instance.username}"
        assert test_instance.password == basic_auth_password, \
            "Password attribute does not match auth tuple." \
            f"Expected: '{basic_auth_password}', configured is '{test_instance.password}"

        assert MockServerRequestHandler.received_auth == expected_auth_value, \
            f"Expected auth header '{expected_auth_value}', " \
            f"server received {MockServerRequestHandler.received_auth}"
        assert MockServerRequestHandler.request_count == expected_request_count, \
            f"Expected {expected_request_count} requests, " \
            f"server received {MockServerRequestHandler.request_count}"

    @aetest.test
    def test_changing_basic_auth_username_attribute(self, basic_auth_username, basic_auth_password, basic_auth_username_alt):

        expected_auth_tuple = (basic_auth_username_alt, basic_auth_password)

        test_class = self.parameters["test_class"]

        if hasattr(test_class, "_instances"):
            test_class._instances = {}

        test_instance = test_class()
        test_instance.auth = (basic_auth_username, basic_auth_password)

        test_instance.username = basic_auth_username_alt

        assert test_instance.auth == expected_auth_tuple, \
            "Changing username did not update the auth tuple as expected.\n" \
            f"Expected: {expected_auth_tuple}\n" \
            f"Configured: {test_instance.auth}"

    @aetest.test
    def test_changing_basic_auth_password_attribute(self, basic_auth_username, basic_auth_password, basic_auth_password_alt):

        expected_auth_tuple = (basic_auth_username, basic_auth_password_alt)

        test_class = self.parameters["test_class"]

        if hasattr(test_class, "_instances"):
            test_class._instances = {}

        test_instance = test_class()
        test_instance.auth = (basic_auth_username, basic_auth_password)

        test_instance.password = basic_auth_password_alt

        assert test_instance.auth == expected_auth_tuple, \
            "Changing username did not update the auth tuple as expected.\n" \
            f"Expected: {expected_auth_tuple}\n" \
            f"Configured: {test_instance.auth}"

    @aetest.test
    def test_basic_auth_header_removed_on_redirect(self, url_path, basic_auth_username, basic_auth_password):
        class FirstMockServerRequestHandler(BaseHTTPRequestHandler):
            server_address = None
            request_count = 0
            next_server = None
            received_auth = None

            def do_GET(self):
                if re.match(f"/{url_path}", self.path):
                    self.__class__.request_count += 1
                    logger.error("Received request")
                    self.__class__.received_auth = self.headers.get("Authorization", None)
                    self.send_response(301)
                    self.send_header(
                        "Content-Type", "application/json; charset=utf-8"
                    )
                    logger.error("Redirecting to %s", self.__class__.next_server)
                    self.send_header("Location", self.__class__.next_server)
                    self.end_headers()
                return

        class TargetMockServerRequestHandler(BaseHTTPRequestHandler):
            server_address = None
            request_count = 0
            received_auth = None

            def do_GET(self):
                if re.match(f"/{url_path}", self.path):
                    self.__class__.request_count += 1
                    logger.error("Got request on the SECOND server")
                    self.__class__.received_auth = self.headers.get("Authorization", None)
                    self.send_response(200)
                    self.send_header(
                        "Content-Type", "application/json; charset=utf-8"
                    )
                    self.end_headers()
                return

        first_test_server = self.start_mock_server(FirstMockServerRequestHandler)
        target_test_server = self.start_mock_server(TargetMockServerRequestHandler)

        logger.error("First target: %s\nSecond target: %s",
                     FirstMockServerRequestHandler.server_address,
                     TargetMockServerRequestHandler.server_address)

        base_url = f"http://{FirstMockServerRequestHandler.server_address}/"
        target_url = f"http://{TargetMockServerRequestHandler.server_address}/{url_path}"

        FirstMockServerRequestHandler.next_server = target_url

        authorization_string = f"{basic_auth_username}:{basic_auth_password}"
        base64_auth = base64.b64encode(bytes(authorization_string, 'utf-8')).decode('utf-8')
        expected_auth_value = f"Basic {base64_auth}"

        expected_request_count = 1

        test_class = self.parameters["test_class"]

        if hasattr(test_class, "_instances"):
            test_class._instances = {}

        test_instance = test_class(base_url=base_url, username=basic_auth_username, password=basic_auth_password)

        try:
            test_instance.get(url_path)
        except Exception as err:
            self.failed(f"Unexpected exception was raised:\n{err}")
        finally:
            self.start_mock_server(first_test_server)
            self.stop_mock_server(target_test_server)

        assert FirstMockServerRequestHandler.request_count == expected_request_count, \
            f"Expected first server to reflect {expected_request_count} requests, " \
            f"Actual was {FirstMockServerRequestHandler.request_count}"
        assert FirstMockServerRequestHandler.received_auth == expected_auth_value, \
            f"First server expected auth header '{expected_auth_value}', " \
            f"server received {FirstMockServerRequestHandler.received_auth}"

        assert TargetMockServerRequestHandler.request_count == expected_request_count, \
            f"Expected target server to reflect {expected_request_count} requests, " \
            f"Actual was {TargetMockServerRequestHandler.request_count}"
        assert TargetMockServerRequestHandler.received_auth is None, \
            f"On redirect, expected second server to NOT receive Authorization header. " \
            f"Instead, server received {TargetMockServerRequestHandler.received_auth}"

    @aetest.test
    def test_custom_auth_header_removed_on_redirect(self, url_path, custom_auth_token_one):
        class FirstMockServerRequestHandler(BaseHTTPRequestHandler):
            server_address = None
            request_count = 0
            next_server = None
            received_auth = None

            def do_GET(self):
                if re.match(f"/{url_path}", self.path):
                    self.__class__.request_count += 1
                    logger.error("Headers received BEFORE redirect:\n%s", self.headers)
                    self.__class__.received_auth = self.headers.get("X-Auth-Token", None)
                    self.send_response(301)
                    self.send_header(
                        "Content-Type", "application/json; charset=utf-8"
                    )
                    self.send_header("Location", self.__class__.next_server)
                    self.end_headers()
                return

        class TargetMockServerRequestHandler(BaseHTTPRequestHandler):
            server_address = None
            request_count = 0
            received_auth = None

            def do_GET(self):
                if re.match(f"/{url_path}", self.path):
                    self.__class__.request_count += 1
                    logger.error("Headers received after redirect:\n%s", self.headers)
                    self.__class__.received_auth = self.headers.get("X-Auth-Token", None)
                    self.send_response(200)
                    self.send_header(
                        "Content-Type", "application/json; charset=utf-8"
                    )
                    self.end_headers()
                return

        first_test_server = self.start_mock_server(FirstMockServerRequestHandler)
        target_test_server = self.start_mock_server(TargetMockServerRequestHandler)

        logger.error("First server: %s\nSecond server: %s", FirstMockServerRequestHandler.server_address, TargetMockServerRequestHandler.server_address)

        base_url = f"http://{FirstMockServerRequestHandler.server_address}/"
        target_url = f"http://{TargetMockServerRequestHandler.server_address}/{url_path}"
        # target_url = f"http://192.168.64.105:19703/"
        FirstMockServerRequestHandler.next_server = target_url

        expected_auth_value = custom_auth_token_one

        expected_request_count = 1

        test_class = self.parameters["test_class"]

        if hasattr(test_class, "_instances"):
            test_class._instances = {}

        test_instance = test_class(base_url=base_url)

        # TODO - Add test_instance.custom_auth_header attribute/setter. For each custom auth header,
        #   remove the key using the new remove_custom_auth_header hook
        test_instance.http.headers.update({"X-Auth-Token": custom_auth_token_one, "Authorization": custom_auth_token_one})
        # test_instance.http.headers

        try:
            test_instance.get(url_path)
        except Exception as err:
            self.failed(f"Unexpected exception was raised:\n{err}")
        finally:
            self.start_mock_server(first_test_server)
            self.stop_mock_server(target_test_server)

        assert FirstMockServerRequestHandler.request_count == expected_request_count, \
            f"Expected first server to reflect {expected_request_count} requests, " \
            f"Actual was {FirstMockServerRequestHandler.request_count}"

        assert FirstMockServerRequestHandler.received_auth == expected_auth_value, \
            f"First server expected auth header '{expected_auth_value}', " \
            f"server received {FirstMockServerRequestHandler.received_auth}"

        assert TargetMockServerRequestHandler.request_count == expected_request_count, \
            f"Expected target server to reflect {expected_request_count} requests, " \
            f"Actual was {TargetMockServerRequestHandler.request_count}"

        assert TargetMockServerRequestHandler.received_auth is None, \
            f"On redirect, expected second server to NOT receive Authorization header. " \
            f"Instead, server received {TargetMockServerRequestHandler.received_auth}"

    @aetest.test
    def test_custom_auth_class(self, url_path, custom_auth_token_one, basic_auth_username, basic_auth_password):
        class AuthMockServerRequestHandler(BaseHTTPRequestHandler):
            server_address = None
            request_count = 0
            received_auth = None

            def do_GET(self):
                if re.match(f"/{url_path}", self.path):
                    self.__class__.request_count += 1

                    self.__class__.received_auth = self.headers.get("Authorization", None)
                    self.send_response(200)
                    self.send_header(
                        "Content-Type", "application/json; charset=utf-8"
                    )
                    self.end_headers()
                    self.wfile.write(bytes(json.dumps({"token": custom_auth_token_one}), "utf-8"))
                return

        class TargetMockServerRequestHandler(BaseHTTPRequestHandler):
            server_address = None
            request_count = 0
            received_auth = None

            def do_GET(self):
                if re.match(f"/{url_path}", self.path):
                    self.__class__.request_count += 1

                    self.__class__.received_auth = self.headers.get("X-Auth-Token", None)
                    self.send_response(200)
                    self.send_header(
                        "Content-Type", "application/json; charset=utf-8"
                    )
                    self.end_headers()
                return

        class ExampleTokenAuth(requests.auth.AuthBase):
            auth_request_count = 0
            header_usage_count = 0

            def __init__(self, auth_url, username, password):
                self.__class__.auth_request_count += 1
                if not hasattr(self, "token"):
                    logger.info("Calling token get")
                    token_result = requests.get(auth_url, auth=(username, password))
                    self.token = token_result.json()["token"]
                else:
                    logger.info("Token already present")

            def __call__(self, r):
                r.headers["X-Auth-Token"] = self.token
                self.__class__.header_usage_count += 1
                return r

        test_server = self.start_mock_server(AuthMockServerRequestHandler)
        target_server = self.start_mock_server(TargetMockServerRequestHandler)

        auth_url = f"http://{AuthMockServerRequestHandler.server_address}/{url_path}"
        target_url = f"http://{TargetMockServerRequestHandler.server_address}/{url_path}"

        expected_auth_request_count = 1
        expected_target_request_count = 2
        expected_auth_header_usage_count = 2

        test_class = self.parameters["test_class"]

        if hasattr(test_class, "_instances"):
            test_class._instances = {}

        # test_instance = test_class(auth=ExampleTokenAuth)
        test_instance = test_class()
        test_instance.auth = ExampleTokenAuth(auth_url=auth_url,
                                              username=basic_auth_username,
                                              password=basic_auth_password)

        try:
            test_instance.get(target_url)
            test_instance.get(target_url)
        except Exception as err:
            self.failed(f"Unexpected exception caught with custom auth class:\n{err}")
        finally:
            self.stop_mock_server(test_server)
            self.stop_mock_server(target_server)

        assert TargetMockServerRequestHandler.received_auth == custom_auth_token_one, \
            "Custom auth header not received.\n" \
            f"Expected: '{custom_auth_token_one}'\n" \
            f"Received: '{TargetMockServerRequestHandler.received_auth}"

        assert AuthMockServerRequestHandler.request_count == expected_auth_request_count, \
            "Request count to auth URL does not match expected.\n" \
            f"Expected: {expected_auth_request_count}, received: {AuthMockServerRequestHandler.request_count}"

        assert TargetMockServerRequestHandler.request_count == expected_target_request_count, \
            "Request count to target URL does not match expected.\n" \
            f"Expected: {expected_auth_request_count}, received: {TargetMockServerRequestHandler.request_count}"

        assert ExampleTokenAuth.auth_request_count == expected_auth_request_count, \
            "Number of token retrievals does not match expected.\n" \
            f"Expected: {expected_auth_request_count}, received: {ExampleTokenAuth.auth_request_count}"

        assert ExampleTokenAuth.header_usage_count == expected_auth_header_usage_count, \
            "Number of times token header was added does not match expected.\n" \
            f"Expected: {expected_auth_header_usage_count}, received: {ExampleTokenAuth.header_usage_count}"

    @aetest.test
    def test_custom_auth_retry_on_failure(self, url_path, custom_auth_token_one, basic_auth_username, basic_auth_password):
        class AuthMockServerRequestHandler(BaseHTTPRequestHandler):
            server_address = None
            request_count = 0
            received_auth = None

            def do_GET(self):
                if re.match(f"/{url_path}", self.path):
                    self.__class__.request_count += 1

                    self.__class__.received_auth = self.headers.get("Authorization", None)
                    self.send_response(200)
                    self.send_header(
                        "Content-Type", "application/json; charset=utf-8"
                    )
                    self.end_headers()
                    self.wfile.write(bytes(json.dumps({"token": custom_auth_token_one}), "utf-8"))
                return

        class TargetMockServerRequestHandler(BaseHTTPRequestHandler):
            server_address = None
            request_count = 0
            received_auth = None

            def do_GET(self):
                if re.match(f"/{url_path}", self.path):
                    self.__class__.request_count += 1
                    if self.__class__.request_count == 1:
                        self.send_response(401)
                        self.send_header(
                            "Content-Type", "application/json; charset=utf-8"
                        )
                    else:
                        self.__class__.received_auth = self.headers.get("X-Auth-Token", None)
                        self.send_response(200)
                        self.send_header(
                            "Content-Type", "application/json; charset=utf-8"
                        )
                    self.end_headers()
                return

        class ExampleTokenAuth(requests.auth.AuthBase):
            auth_request_count = 0
            header_usage_count = 0

            def __init__(self, auth_url, username, password):
                self.auth_url = auth_url
                self.username = username
                self.password = password
                self.token = None

                # if not hasattr(self, "token"):
                if not self.token:
                    logger.info("Calling token get")
                    self.reauth()
                else:
                    logger.info("Token already present")

            def __call__(self, r):
                r.headers["X-Auth-Token"] = self.token
                self.__class__.header_usage_count += 1
                return r

            def reauth(self):
                self.__class__.auth_request_count += 1
                token_result = requests.get(self.auth_url, auth=(self.username, self.password))
                self.token = token_result.json()["token"]

        test_server = self.start_mock_server(AuthMockServerRequestHandler)
        target_server = self.start_mock_server(TargetMockServerRequestHandler)

        auth_url = f"http://{AuthMockServerRequestHandler.server_address}/{url_path}"
        target_url = f"http://{TargetMockServerRequestHandler.server_address}/{url_path}"

        expected_auth_request_count = 2
        expected_target_request_count = 3
        expected_auth_header_usage_count = 2

        test_class = self.parameters["test_class"]

        if hasattr(test_class, "_instances"):
            test_class._instances = {}

        # test_instance = test_class(auth=ExampleTokenAuth)
        test_instance = test_class()
        test_instance.auth = ExampleTokenAuth(auth_url=auth_url,
                                              username=basic_auth_username,
                                              password=basic_auth_password)

        def auth_response_hook(response, **kwargs):  # pylint: disable=unused-argument
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError:
                if response.status_code == 401:
                    # test_instance.http.auth.reauth()
                    test_instance.reauth()
                    logger.error("Resending request...")
                    return test_instance.http.send(response.request)

        # test_instance.add_response_hooks(auth_response_hook)
        test_instance.replace_response_hooks(auth_response_hook)

        try:
            test_instance.get(target_url)
            test_instance.get(target_url)
            # test_instance.get(f"http://{TargetMockServerRequestHandler.server_address}/noplace")
        except Exception as err:
            self.failed(f"Unexpected exception caught with custom auth class:\n{err}")
        finally:
            self.stop_mock_server(test_server)
            self.stop_mock_server(target_server)

        assert len(test_instance.response_hooks) == 1, \
            "Response hook should have been replaced with desired. " \
            f"Instead, there are {len(test_instance.response_hooks)} hooks configured."

        assert TargetMockServerRequestHandler.received_auth == custom_auth_token_one, \
            "Custom auth header not received.\n" \
            f"Expected: '{custom_auth_token_one}'\n" \
            f"Received: '{TargetMockServerRequestHandler.received_auth}"

        assert AuthMockServerRequestHandler.request_count == expected_auth_request_count, \
            "Request count to auth URL does not match expected.\n" \
            f"Expected: {expected_auth_request_count}, received: {AuthMockServerRequestHandler.request_count}"

        assert TargetMockServerRequestHandler.request_count == expected_target_request_count, \
            "Request count to target URL does not match expected.\n" \
            f"Expected: {expected_auth_request_count}, received: {TargetMockServerRequestHandler.request_count}"

        assert ExampleTokenAuth.auth_request_count == expected_auth_request_count, \
            "Number of token retrievals does not match expected.\n" \
            f"Expected: {expected_auth_request_count}, received: {ExampleTokenAuth.auth_request_count}"

        assert ExampleTokenAuth.header_usage_count == expected_auth_header_usage_count, \
            "Number of times token header was added does not match expected.\n" \
            f"Expected: {expected_auth_header_usage_count}, received: {ExampleTokenAuth.header_usage_count}"

    @aetest.test
    def test_add_custom_auth_retry(self, url_path, request_retry_count, custom_auth_token_one, custom_auth_token_two, basic_auth_username, basic_auth_password):
        class AuthMockServerRequestHandler(BaseHTTPRequestHandler):
            server_address = None
            request_count = 0
            received_auth = None

            def do_GET(self):
                if re.match(f"/{url_path}", self.path):
                    self.__class__.request_count += 1
                    if self.__class__.request_count == 1:
                        self.__class__.received_auth = self.headers.get("Authorization", None)
                        self.send_response(200)
                        self.send_header(
                            "Content-Type", "application/json; charset=utf-8"
                        )
                        self.end_headers()
                        self.wfile.write(bytes(json.dumps({"token": custom_auth_token_one}), "utf-8"))
                    else:
                        self.__class__.received_auth = self.headers.get("Authorization", None)
                        self.send_response(200)
                        self.send_header(
                            "Content-Type", "application/json; charset=utf-8"
                        )
                        self.end_headers()
                        self.wfile.write(bytes(json.dumps({"token": custom_auth_token_two}), "utf-8"))

                return

        class TargetMockServerRequestHandler(BaseHTTPRequestHandler):
            server_address = None
            request_count = 0
            received_auth = None

            def do_GET(self):
                if re.match(f"/{url_path}", self.path):
                    self.__class__.request_count += 1
                    if self.__class__.request_count == 1:
                        self.send_response(401)
                        self.send_header(
                            "Content-Type", "application/json; charset=utf-8"
                        )
                    else:
                        self.__class__.received_auth = self.headers.get("X-Auth-Token", None)
                        self.send_response(503)  # TODO Another test with 401 for max reauth
                        self.send_header(
                            "Content-Type", "application/json; charset=utf-8"
                        )
                    self.end_headers()
                return

        class ExampleTokenAuth(requests.auth.AuthBase):
            auth_request_count = 0
            header_usage_count = 0

            def __init__(self, auth_url, username, password):
                self.auth_url = auth_url
                self.username = username
                self.password = password
                self.token = None

                # if not hasattr(self, "token"):
                if not self.token:
                    logger.info("Calling token get")
                    self.reauth()
                else:
                    logger.info("Token already present")

            def __call__(self, r):
                logger.error("Calling the auth token instance")
                r.headers["X-Auth-Token"] = self.token
                self.__class__.header_usage_count += 1
                return r

            def reauth(self):
                self.__class__.auth_request_count += 1
                token_result = requests.get(self.auth_url, auth=(self.username, self.password))
                self.token = token_result.json()["token"]
                return self

        test_server = self.start_mock_server(AuthMockServerRequestHandler)
        target_server = self.start_mock_server(TargetMockServerRequestHandler)

        auth_url = f"http://{AuthMockServerRequestHandler.server_address}/{url_path}"
        base_url = f"http://{TargetMockServerRequestHandler.server_address}"

        # First auth will fail, expect one more auth attempt for the
        # successful response
        expected_auth_request_count = 2

        # Retry + 1 for the 503 errors plus 1 for the initial 401
        expected_target_request_count = request_retry_count + 2

        # Expected:
        # 1 usage for the request that gets a 401
        # 1 usage for the request retry
        expected_auth_header_usage_count = 2

        test_class = self.parameters["test_class"]

        if hasattr(test_class, "_instances"):
            test_class._instances = {}

        # test_instance = test_class(auth=ExampleTokenAuth)
        test_instance = test_class(base_url=base_url,
                                   retry=request_retry_count,
                                   auth=ExampleTokenAuth(auth_url=auth_url,
                                                         username=basic_auth_username,
                                                         password=basic_auth_password)
                                   )

        def auth_response_hook(response, **kwargs):  # pylint: disable=unused-argument
            logger.error("Response hook locals: %s", locals())
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError:
                if response.status_code == 401:
                    test_instance.reauth()
                    return test_instance.request(response.request.method,
                                                 response.request.url,
                                                 data=response.request.body)

        # test_instance.add_response_hooks(auth_response_hook)
        test_instance.replace_response_hooks(auth_response_hook)

        try:
            test_instance.get(url_path)
        except requests.exceptions.RetryError:
            logger.info("Expected RetryError was caught, continuing")
        else:
            self.failed("RetryError was NOT caught, failing early.")
        finally:
            self.stop_mock_server(test_server)
            self.stop_mock_server(target_server)


        # test_instance.get(f"http://{TargetMockServerRequestHandler.server_address}/noplace")
        # self.stop_mock_server(test_server)
        # self.stop_mock_server(target_server)

        assert len(test_instance.response_hooks) == 1, \
            "Response hook should have been replaced with desired. " \
            f"Instead, there are {len(test_instance.response_hooks)} hooks configured."

        assert TargetMockServerRequestHandler.received_auth == custom_auth_token_two, \
            "Custom auth header not received.\n" \
            f"Expected: '{custom_auth_token_two}'\n" \
            f"Received: '{TargetMockServerRequestHandler.received_auth}"

        assert AuthMockServerRequestHandler.request_count == expected_auth_request_count, \
            "Request count to auth URL does not match expected.\n" \
            f"Expected: {expected_auth_request_count}, received: {AuthMockServerRequestHandler.request_count}"

        assert TargetMockServerRequestHandler.request_count == expected_target_request_count, \
            "Request count to target URL does not match expected.\n" \
            f"Expected: {expected_auth_request_count}, received: {TargetMockServerRequestHandler.request_count}"

        assert ExampleTokenAuth.auth_request_count == expected_auth_request_count, \
            "Number of token retrievals does not match expected.\n" \
            f"Expected: {expected_auth_request_count}, received: {ExampleTokenAuth.auth_request_count}"

        assert ExampleTokenAuth.header_usage_count == expected_auth_header_usage_count, \
            "Number of times token header was added does not match expected.\n" \
            f"Expected: {expected_auth_header_usage_count}, received: {ExampleTokenAuth.header_usage_count}"


