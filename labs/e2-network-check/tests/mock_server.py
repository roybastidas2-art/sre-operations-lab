#!/usr/bin/env python3
"""Servicio local de prueba. Escucha solo en 127.0.0.1."""
import argparse
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/slow":
            time.sleep(2.2)
        if self.path == "/unhealthy":
            status, body = 503, b'{"status":"unhealthy"}'
        elif self.path == "/business-error":
            status, body = 200, b'{"status":"error","detail":"operation rejected"}'
        elif self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/health")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        elif self.path in ("/health", "/slow"):
            status, body = 200, b'{"status":"ok"}'
        else:
            status, body = 404, b'{"status":"not_found"}'
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            # Normal si curl interrumpe una solicitud por timeout.
            pass

    def log_message(self, fmt, *args):
        print("HTTP", fmt % args, flush=True)


def main():
    parser = argparse.ArgumentParser(description="Servidor HTTP local para Semana 2")
    parser.add_argument("--port", type=int, default=8088)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port debe estar entre 1 y 65535")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Servidor de pruebas: http://127.0.0.1:{args.port}/health", flush=True)
    print("Rutas: /health /unhealthy /business-error /slow /redirect", flush=True)
    print("Finalizar: Ctrl+C", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
