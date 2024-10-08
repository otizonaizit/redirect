# pylint: disable=missing-module-docstring,missing-class-docstring,invalid-name

import http.server
import socket
import socketserver
import ssl
import subprocess
import sys

from pathlib import Path
from systemd import daemon

PORT = 8080
CGI = 'play.cgi'

our_dir = Path(__file__).parent

PAGE = ('''\
<html>
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    <title>Gotcha</title>
    <style>
     html { font-size: 15vw; text-align: center }
    </style>
  </head>
  <body>
      👮<br>GOTCHA!<br>👮
  </body>
</html>
''').encode()

class Redirect(http.server.CGIHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        self.wfile.write(PAGE)

        cmd = ['systemd-run', 'amixer', 'sset', 'Master', '100%', 'unmute']
        subprocess.call(cmd)

        cmd = ['systemd-run', '-d', '--user', 'mpv', 'police.opus']
        subprocess.check_call(cmd)


class SocketActivatedServer(http.server.HTTPServer):
    # pylint: disable=non-parent-init-called,super-init-not-called
    def __init__(self, RequestHandlerClass, bind_and_activate=True):
        assert bind_and_activate

        fd, = daemon.listen_fds()
        print(f'got {fd=}')
        sock = socket.fromfd(fd, self.address_family, self.socket_type)

        server_address = sock.getsockname()[:2]
        print(f'{server_address=}')

        socketserver.BaseServer.__init__(self, server_address, RequestHandlerClass)

        self.socket = sock


with SocketActivatedServer(Redirect) as httpd:
    if len(sys.argv) > 1 and sys.argv[1] == '--ssl':
        # pylint: disable=attribute-defined-outside-init
        httpd.have_fork = False
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(certfile="ssl/openai.com+4.pem",
                            keyfile="ssl/openai.com+4-key.pem")
        httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)

    httpd.serve_forever()
