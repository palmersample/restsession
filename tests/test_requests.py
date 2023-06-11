import logging
from BaseHttpServer import BaseHttpServer
from pyats import aetest
# from src import HttpSessionClass, HttpSessionSingletonClass
from requests.exceptions import MissingSchema
from http.server import BaseHTTPRequestHandler
import re
import json

logger = logging.getLogger(__name__)


class TestBasicRequests(BaseHttpServer):

    @aetest.test
    def test_base_url_failure(self, url_path):
        test_class = self.parameters["test_class"]

        if hasattr(test_class, "_instances"):
            test_class._instances = {}

        test_instance = test_class()

        logger.info("Sending GET request to invalid URL: %s", url_path)
        try:
            test_instance.get(url_path)
        except MissingSchema:
            self.passed("MissingSchema exception caught as expected")
        else:
            self.failed("MissingSchema exception was NOT caught")

    @aetest.test
    def test_get_explicit_url(self, url_path):
        class MockServerRequestHandler(BaseHTTPRequestHandler):
            server_address = None
            request_count = 0

            def do_GET(self):
                if re.match(f"/{url_path}", self.path):
                    self.__class__.request_count += 1

                    self.send_response(200)
                    self.send_header(
                        "Content-Type", "application/json; charset=utf-8"
                    )
                    self.end_headers()
                return

        test_server = self.start_mock_server(MockServerRequestHandler)
        test_url = f"http://{MockServerRequestHandler.server_address}/{url_path}"

        test_class = self.parameters["test_class"]

        if hasattr(test_class, "_instances"):
            test_class._instances = {}

        test_instance = test_class()

        try:
            response = test_instance.get(test_url)
        except Exception as err:
            self.failed(f"Unexpected exception was raised:\n{err}")
        finally:
            self.stop_mock_server(test_server)

        assert response.ok, "Non-OK response code received"
        assert MockServerRequestHandler.request_count == 1, \
            f"Expected 1 request, server received {MockServerRequestHandler.request_count}"

    # Remaining tests will use a base URL
    @aetest.test
    def test_get(self, url_path):
        class MockServerRequestHandler(BaseHTTPRequestHandler):
            server_address = None
            request_count = 0

            def do_GET(self):
                if re.match(f"/{url_path}", self.path):
                    self.__class__.request_count += 1

                    self.send_response(200)
                    self.send_header(
                        "Content-Type", "application/json; charset=utf-8"
                    )
                    self.end_headers()
                return

        test_server = self.start_mock_server(MockServerRequestHandler)
        base_url = f"http://{MockServerRequestHandler.server_address}"

        test_class = self.parameters["test_class"]

        if hasattr(test_class, "_instances"):
            test_class._instances = {}

        test_instance = test_class(base_url=base_url)

        try:
            response = test_instance.get(url_path)
        except Exception as err:
            self.failed(f"Unexpected exception was raised:\n{err}")
        finally:
            self.stop_mock_server(test_server)

        assert response.ok, "Non-OK response code received"
        assert MockServerRequestHandler.request_count == 1, \
            f"Expected 1 request, server received {MockServerRequestHandler.request_count}"

    @aetest.test
    def test_post(self, url_path, test_payload):
        class MockServerRequestHandler(BaseHTTPRequestHandler):
            request_count = 0
            received_payload = None

            def do_POST(self):
                # logger.info("POST received. Request dir:\n%sResponse dir:\n%s", dir(self.request), dir(self.responses))
                if re.match(f"/{url_path}", self.path):
                    self.__class__.request_count += 1

                    content_length = int(self.headers.get("Content-Length", 0))
                    post_body = self.rfile.read(content_length).decode("utf-8")

                    # Received POST body was JSON-encoded, just read and save.
                    self.__class__.received_payload = post_body
                    logger.info("POST Length: %s\nBody:\n%s", content_length, post_body)
                    self.send_response(200, message="OK")
                    self.send_header(
                        "Content-Type", "application/json; charset=utf-8"
                    )
                    self.end_headers()
                    self.wfile.write(bytes(json.dumps({"Result": "OK"}), "utf-8"))

                    # self.wfile.write(json.dumps({}).encode("utf-8"))
                return

        test_server = self.start_mock_server(MockServerRequestHandler)
        base_url = f"http://{MockServerRequestHandler.server_address}"

        test_class = self.parameters["test_class"]

        if hasattr(test_class, "_instances"):
            test_class._instances = {}

        test_instance = test_class(base_url=base_url)

        try:
            response = test_instance.post(url=url_path, json=test_payload)
        except Exception as err:
            self.failed(f"Unexpected exception was raised:\n{err}")
        finally:
            self.stop_mock_server(test_server)

        assert response.ok, "Non-OK response code received"
        assert MockServerRequestHandler.request_count == 1, \
            f"Expected 1 request, server received {MockServerRequestHandler.request_count}"
        assert MockServerRequestHandler.received_payload == json.dumps(test_payload), \
            f"Received payload does not match!\n" \
            f"Sent payload:\n{json.dumps(test_payload)}\n" \
            f"Received payload:\n{MockServerRequestHandler.received_payload}"

    @aetest.test
    def test_put(self, url_path, test_payload):

        class MockServerRequestHandler(BaseHTTPRequestHandler):
            request_count = 0
            received_payload = None

            def do_PUT(self):
                # logger.info("POST received. Request dir:\n%sResponse dir:\n%s", dir(self.request), dir(self.responses))
                if re.match(f"/{url_path}", self.path):
                    self.__class__.request_count += 1

                    content_length = int(self.headers.get("Content-Length", 0))
                    post_body = self.rfile.read(content_length).decode("utf-8")

                    # Received POST body was JSON-encoded, just read and save.
                    self.__class__.received_payload = post_body
                    logger.info("POST Length: %s\nBody:\n%s", content_length, post_body)
                    self.send_response(200, message="OK")
                    self.send_header(
                        "Content-Type", "application/json; charset=utf-8"
                    )
                    self.end_headers()
                    self.wfile.write(bytes(json.dumps({"Result": "OK"}), "utf-8"))

                    # self.wfile.write(json.dumps({}).encode("utf-8"))
                return

        test_server = self.start_mock_server(MockServerRequestHandler)
        base_url = f"http://{MockServerRequestHandler.server_address}"

        test_class = self.parameters["test_class"]

        if hasattr(test_class, "_instances"):
            test_class._instances = {}

        test_instance = test_class(base_url=base_url)

        try:
            response = test_instance.put(url=url_path, json=test_payload)
        except Exception as err:
            self.failed(f"Unexpected exception was raised:\n{err}")
        finally:
            self.stop_mock_server(test_server)

        assert response.ok, "Non-OK response code received"
        assert MockServerRequestHandler.request_count == 1, \
            f"Expected 1 request, server received {MockServerRequestHandler.request_count}"
        assert MockServerRequestHandler.received_payload == json.dumps(test_payload), \
            f"Received payload does not match!\n" \
            f"Sent payload:\n{json.dumps(test_payload)}\n" \
            f"Received payload:\n{MockServerRequestHandler.received_payload}"

    @aetest.test
    def test_patch(self, url_path, test_payload):
        class MockServerRequestHandler(BaseHTTPRequestHandler):
            request_count = 0
            received_payload = None

            def do_PATCH(self):
                # logger.info("POST received. Request dir:\n%sResponse dir:\n%s", dir(self.request), dir(self.responses))
                if re.match(f"/{url_path}", self.path):
                    self.__class__.request_count += 1

                    content_length = int(self.headers.get("Content-Length", 0))
                    post_body = self.rfile.read(content_length).decode("utf-8")

                    # Received POST body was JSON-encoded, just read and save.
                    self.__class__.received_payload = post_body
                    logger.info("POST Length: %s\nBody:\n%s", content_length, post_body)
                    self.send_response(200, message="OK")
                    self.send_header(
                        "Content-Type", "application/json; charset=utf-8"
                    )
                    self.end_headers()
                    self.wfile.write(bytes(json.dumps({"Result": "OK"}), "utf-8"))

                    # self.wfile.write(json.dumps({}).encode("utf-8"))
                return

        test_server = self.start_mock_server(MockServerRequestHandler)
        base_url = f"http://{MockServerRequestHandler.server_address}"

        test_class = self.parameters["test_class"]

        if hasattr(test_class, "_instances"):
            test_class._instances = {}

        test_instance = test_class(base_url=base_url)

        try:
            response = test_instance.patch(url=url_path, json=test_payload)
        except Exception as err:
            self.failed(f"Unexpected exception was raised:\n{err}")
        finally:
            self.stop_mock_server(test_server)

        assert response.ok, "Non-OK response code received"
        assert MockServerRequestHandler.request_count == 1, \
            f"Expected 1 request, server received {MockServerRequestHandler.request_count}"
        assert MockServerRequestHandler.received_payload == json.dumps(test_payload), \
            f"Received payload does not match!\n" \
            f"Sent payload:\n{json.dumps(test_payload)}\n" \
            f"Received payload:\n{MockServerRequestHandler.received_payload}"


    @aetest.test
    def test_options(self):

        class MockServerRequestHandler(BaseHTTPRequestHandler):
            request_count = 0

            def do_OPTIONS(self):
                self.__class__.request_count += 1

                self.send_response(204, message="No Content")
                self.send_header(
                    "Content-Type", "application/json; charset=utf-8",
                )
                self.end_headers()
                return

        test_server = self.start_mock_server(MockServerRequestHandler)
        base_url = f"http://{MockServerRequestHandler.server_address}"

        test_class = self.parameters["test_class"]

        if hasattr(test_class, "_instances"):
            test_class._instances = {}

        test_instance = test_class(base_url=base_url)

        try:
            response = test_instance.options(url="*")
        except Exception as err:
            self.failed(f"Unexpected exception was raised:\n{err}")
        finally:
            self.stop_mock_server(test_server)

        assert response.ok, "Non-OK response code received"
        assert MockServerRequestHandler.request_count == 1, \
            f"Expected 1 request, server received {MockServerRequestHandler.request_count}"


    @aetest.test
    def test_head(self, url_path):

        class MockServerRequestHandler(BaseHTTPRequestHandler):
            request_count = 0

            def do_HEAD(self):
                if re.match(f"/{url_path}", self.path):
                    self.__class__.request_count += 1

                    self.send_response(204, message="No Content")
                    self.send_header(
                        "Content-Type", "application/json; charset=utf-8",
                    )
                    self.end_headers()
                return

        test_server = self.start_mock_server(MockServerRequestHandler)
        base_url = f"http://{MockServerRequestHandler.server_address}"

        test_class = self.parameters["test_class"]

        if hasattr(test_class, "_instances"):
            test_class._instances = {}

        test_instance = test_class(base_url=base_url)

        try:
            response = test_instance.head(url=url_path)
        except Exception as err:
            self.failed(f"Unexpected exception was raised:\n{err}")
        finally:
            self.stop_mock_server(test_server)

        assert response.ok, "Non-OK response code received"
        assert MockServerRequestHandler.request_count == 1, \
            f"Expected 1 request, server received {MockServerRequestHandler.request_count}"

    @aetest.test
    def test_delete(self, url_path):

        class MockServerRequestHandler(BaseHTTPRequestHandler):
            server_address = None
            request_count = 0

            def do_DELETE(self):
                if re.match(f"/{url_path}", self.path):
                    self.__class__.request_count += 1

                    self.send_response(204, message="No Content")
                    self.send_header(
                        "Content-Type", "application/json; charset=utf-8"
                    )
                    self.end_headers()
                return

        test_server = self.start_mock_server(MockServerRequestHandler)
        base_url = f"http://{MockServerRequestHandler.server_address}"

        test_class = self.parameters["test_class"]

        if hasattr(test_class, "_instances"):
            test_class._instances = {}

        test_instance = test_class(base_url=base_url)

        try:
            response = test_instance.delete(url_path)
        except Exception as err:
            self.failed(f"Unexpected exception was raised:\n{err}")
        finally:
            self.stop_mock_server(test_server)

        assert response.ok, "Non-OK response code received"
        assert MockServerRequestHandler.request_count == 1, \
            f"Expected 1 request, server received {MockServerRequestHandler.request_count}"


    @aetest.test
    def test_non_standard_verb(self, url_path, test_payload):
        class MockServerRequestHandler(BaseHTTPRequestHandler):
            request_count = 0
            received_payload = None

            def do_BOGUS(self):
                # logger.info("POST received. Request dir:\n%sResponse dir:\n%s", dir(self.request), dir(self.responses))
                if re.match(f"/{url_path}", self.path):
                    self.__class__.request_count += 1

                    content_length = int(self.headers.get("Content-Length", 0))
                    post_body = self.rfile.read(content_length).decode("utf-8")

                    # Received POST body was JSON-encoded, just read and save.
                    self.__class__.received_payload = post_body
                    logger.info("POST Length: %s\nBody:\n%s", content_length, post_body)
                    self.send_response(200, message="OK")
                    self.send_header(
                        "Content-Type", "application/json; charset=utf-8"
                    )
                    self.end_headers()
                    self.wfile.write(bytes(json.dumps({"Result": "OK"}), "utf-8"))

                    # self.wfile.write(json.dumps({}).encode("utf-8"))
                return

        test_server = self.start_mock_server(MockServerRequestHandler)
        base_url = f"http://{MockServerRequestHandler.server_address}"

        test_class = self.parameters["test_class"]

        if hasattr(test_class, "_instances"):
            test_class._instances = {}

        test_instance = test_class(base_url=base_url)

        try:
            response = test_instance.request("bogus", url=url_path, json=test_payload)
        except Exception as err:
            self.failed(f"Unexpected exception was raised:\n{err}")
        finally:
            self.stop_mock_server(test_server)

        assert response.ok, "Non-OK response code received"
        assert MockServerRequestHandler.request_count == 1, \
            f"Expected 1 request, server received {MockServerRequestHandler.request_count}"
        assert MockServerRequestHandler.received_payload == json.dumps(test_payload), \
            f"Received payload does not match!\n" \
            f"Sent payload:\n{json.dumps(test_payload)}\n" \
            f"Received payload:\n{MockServerRequestHandler.received_payload}"

