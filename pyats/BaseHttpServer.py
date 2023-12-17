import logging
from http.server import HTTPServer
import socket
from threading import Thread
from pyats import aetest


logger = logging.getLogger(__name__)


class BaseHttpServer(aetest.Testcase):

    mock_servers = {}

    def get_free_port(self, bind_address="localhost"):
        s = socket.socket(socket.AF_INET, type=socket.SOCK_STREAM)
        s.bind((bind_address, 0))
        address, port = s.getsockname()
        s.close()
        return port

    def stop_mock_server(self, mock_server):
        if server_thread := self.__class__.mock_servers.get(mock_server, None):
            mock_server.shutdown()
            mock_server.server_close()
            server_thread.join()
            del self.__class__.mock_servers[mock_server]

    def start_mock_server(self, handler, bind_address="localhost"):

        server_port = self.get_free_port(bind_address)
        mock_server = HTTPServer((bind_address, server_port), handler)

        handler.server_address = f"{bind_address}:{server_port}"

        mock_server_thread = Thread(target=mock_server.serve_forever)
        mock_server_thread.daemon = True
        mock_server_thread.start()

        self.__class__.mock_servers[mock_server] = mock_server_thread
        return mock_server
    #
    # @aetest.setup
    # def set_webserver_attibute(self):
    #     setattr(self, "webserver", self.setup_mock_server)
