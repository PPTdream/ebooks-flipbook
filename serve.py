#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""本地预览用的极简静态服务器（规避 Windows 中文主机名导致 http.server 崩溃）。"""
import os
import sys
import functools
import http.server
import socketserver

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

    def server_bind(self):
        self.socket.bind(self.server_address)
        self.server_name = "localhost"
        self.server_port = self.server_address[1]


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8099
    handler = functools.partial(Handler, directory=ROOT)
    with Server(("127.0.0.1", port), handler) as httpd:
        sys.stderr.write("serving %s on http://127.0.0.1:%d\n" % (ROOT, port))
        sys.stderr.flush()
        httpd.serve_forever()


if __name__ == "__main__":
    main()
