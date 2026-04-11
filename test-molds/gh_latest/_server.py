"""Fake GitHub releases server for e2e tests.

Usage: uv run _server.py <port_file> <tag>

Responds 302 with Location header on /releases/latest, simulating GitHub's redirect.
Supports multiple paths:
  /releases/latest         — 302 redirect to /releases/tag/<tag>
  /no-release/releases/latest — 200 with no Location (simulates repo without releases)
Writes the bound port to <port_file> once ready.
"""

import http.server
import sys


def main():
    port_file = sys.argv[1]
    tag = sys.argv[2]

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/no-release/releases/latest":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"No releases found")
            elif "/releases/latest" in self.path:
                self.send_response(302)
                self.send_header(
                    "Location",
                    f"https://github.com/org/repo/releases/tag/{tag}",
                )
                self.end_headers()
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, *_):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    with open(port_file, "w") as f:
        f.write(str(srv.server_address[1]))
    srv.serve_forever()


if __name__ == "__main__":
    main()
