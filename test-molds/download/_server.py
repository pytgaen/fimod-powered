"""Fake file server for e2e tests.

Usage: uv run _server.py <port_file> <content>

Serves <content> as a binary download on any GET request.
Writes the bound port to <port_file> once ready.
"""

import http.server
import sys


def main():
    port_file = sys.argv[1]
    content = sys.argv[2].encode()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.end_headers()
            self.wfile.write(content)

        def log_message(self, *_):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    with open(port_file, "w") as f:
        f.write(str(srv.server_address[1]))
    srv.serve_forever()


if __name__ == "__main__":
    main()
