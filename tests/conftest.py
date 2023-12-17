import pytest
import logging
from http.server import HTTPServer
import socket
from threading import Thread
from requests_toolbelt.sessions import BaseUrlSession
from restsession import RestSession, RestSessionSingleton

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session",
                params=[BaseUrlSession,
                        RestSession])
def standard_test_class(request):
    yield request.param


@pytest.fixture(scope="session",
                params=[RestSessionSingleton])
def singleton_test_class(request):
    yield request.param


@pytest.fixture(scope="session",
                params=[BaseUrlSession,
                        RestSession,
                        RestSessionSingleton])
def test_class(request):
    yield request.param


@pytest.fixture(autouse=True, scope="function")
def reset_singleton():
    RestSessionSingleton._instances = {}


class BaseHttpServer:

    mock_servers = {}

    def __enter__(self):
        return self

    def __exit__(self):
        self.stop_mock_server()

    def stop_mock_server(self, mock_server):
        for server in self.__class__.mock_servers:
        # if server_thread := self.__class__.mock_servers.get(mock_server, None):
            if server_thread := server:
                server.shutdown()
                server.server_close()
                server_thread.join()
                del self.__class__.mock_servers[mock_server]

    def __init__(self, handler, bind_address="localhost"):
        def get_free_port():
            s = socket.socket(socket.AF_INET, type=socket.SOCK_STREAM)
            s.bind((bind_address, 0))
            address, port = s.getsockname()
            s.close()
            return port

        server_port = get_free_port()
        mock_server = HTTPServer((bind_address, server_port), handler)

        handler.server_address = f"{bind_address}:{server_port}"

        mock_server_thread = Thread(target=mock_server.serve_forever)
        mock_server_thread.daemon = True
        mock_server_thread.start()

        self.handler = handler
        self.url = f"http://{handler.server_address}"
        self.__class__.mock_servers[mock_server] = mock_server_thread
        # return mock_server