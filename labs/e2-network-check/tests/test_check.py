#!/usr/bin/env python3
"""Pruebas sin dependencias externas; se ejecutan en localhost."""
import json
import socket
import subprocess
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check.sh"


class LocalHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/slow":
            time.sleep(2.2)
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/health")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if self.path == "/unhealthy":
            status, data = 503, b'{"status":"unhealthy"}'
        elif self.path == "/business-error":
            # La aplicación indica un error funcional pese a devolver HTTP 200.
            status, data = 200, b'{"status":"error"}'
        else:
            status, data = 200, b'{"status":"ok"}'
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            # Esperado en pruebas con timeout del cliente.
            pass

    def log_message(self, *_args):
        pass


class CheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), LocalHandler)
        cls.server.daemon_threads = True
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name) / "checks.jsonl"

    def run_check(self, *, path="/health", port=None, url=None, extra=()):
        port = self.port if port is None else port
        url = url if url is not None else f"http://127.0.0.1:{self.port}{path}"
        cmd = [
            "bash", str(SCRIPT),
            "--url", url,
            "--tcp-host", "127.0.0.1",
            "--tcp-port", str(port),
            "--timeout", "3",
            "--label", "local-test",
            "--output", str(self.out),
            *extra,
        ]
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=15, check=False)
        try:
            record = json.loads(proc.stdout.strip())
        except json.JSONDecodeError:
            self.fail(f"Salida no JSON. stdout={proc.stdout!r} stderr={proc.stderr!r}")
        return proc, record

    def test_http_200_and_tcp_ok(self):
        proc, record = self.run_check()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(record["http"]["ok"])
        self.assertTrue(record["tcp"]["ok"])
        self.assertTrue(record["overall_ok"])
        self.assertEqual(record["http"]["status"], 200)
        self.assertGreaterEqual(record["tcp"]["elapsed_ms"], 0)
        self.assertEqual(record["schema_version"], 1)
        saved = self.out.read_text().strip().splitlines()
        self.assertEqual(len(saved), 1)
        self.assertEqual(json.loads(saved[0]), record)

    def test_http_200_does_not_prove_functional_health(self):
        proc, record = self.run_check(path="/business-error")
        # Límite intencionado: el comprobador NO inspecciona el JSON de negocio.
        self.assertEqual(proc.returncode, 0)
        self.assertTrue(record["http"]["ok"])
        self.assertTrue(record["overall_ok"])

    def test_unexpected_http_503_but_tcp_ok(self):
        proc, record = self.run_check(path="/unhealthy")
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(record["http"]["status"], 503)
        self.assertEqual(record["http"]["error"], "HTTP_STATUS_UNEXPECTED")
        self.assertFalse(record["http"]["ok"])
        self.assertTrue(record["tcp"]["ok"])
        self.assertFalse(record["overall_ok"])

    def test_expect_503_can_be_configured(self):
        proc, record = self.run_check(path="/unhealthy", extra=("--expect-status", "503"))
        self.assertEqual(proc.returncode, 0)
        self.assertTrue(record["http"]["ok"])
        self.assertEqual(record["http"]["expected_status"], 503)

    def test_tcp_closed_but_http_ok(self):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            unused_port = s.getsockname()[1]
        proc, record = self.run_check(port=unused_port)
        self.assertEqual(proc.returncode, 1)
        self.assertTrue(record["http"]["ok"])
        self.assertFalse(record["tcp"]["ok"])
        self.assertEqual(record["tcp"]["error"], "CONNECTION_ERROR")

    def test_http_timeout(self):
        proc, record = self.run_check(path="/slow", extra=("--timeout", "1"))
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(record["http"]["error"], "TIMEOUT")
        self.assertTrue(record["tcp"]["ok"])

    def test_dns_error(self):
        proc, record = self.run_check(url="http://missing-host.example.invalid/", extra=("--timeout", "3"))
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(record["http"]["error"], "DNS_ERROR", record)
        self.assertTrue(record["tcp"]["ok"])

    def test_rejects_invalid_port(self):
        proc = subprocess.run(
            ["bash", str(SCRIPT), "--url", "http://localhost/", "--tcp-host", "localhost", "--tcp-port", "70000"],
            text=True, capture_output=True, timeout=10, check=False,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("fuera del rango", proc.stderr)

    def test_rejects_url_credentials(self):
        proc = subprocess.run(
            ["bash", str(SCRIPT), "--url", "https://user:secret@example.com/", "--tcp-host", "example.com", "--tcp-port", "443"],
            text=True, capture_output=True, timeout=10, check=False,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertNotIn("user:secret@", proc.stderr)

    def test_appends_multiple_jsonl_records(self):
        self.run_check()
        self.run_check(path="/unhealthy")
        records = [json.loads(line) for line in self.out.read_text().splitlines()]
        self.assertEqual(len(records), 2)
        self.assertTrue(records[0]["overall_ok"])
        self.assertFalse(records[1]["overall_ok"])


    def test_redirect_is_not_followed(self):
        proc, record = self.run_check(path="/redirect")
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(record["http"]["status"], 302)
        self.assertEqual(record["http"]["error"], "HTTP_STATUS_UNEXPECTED")
        self.assertTrue(record["tcp"]["ok"])

    def test_expected_302_is_allowed(self):
        proc, record = self.run_check(path="/redirect", extra=("--expect-status", "302"))
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(record["http"]["status"], 302)
        self.assertTrue(record["overall_ok"])

    def test_rejects_timeout_zero(self):
        proc = subprocess.run(
            ["bash", str(SCRIPT), "--url", "http://localhost/", "--tcp-host", "localhost", "--tcp-port", "80", "--timeout", "0"],
            text=True, capture_output=True, timeout=10, check=False,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("--timeout", proc.stderr)

    def test_rejects_query_string_in_url(self):
        proc = subprocess.run(
            ["bash", str(SCRIPT), "--url", "http://localhost/health?token=SECRET_TEST", "--tcp-host", "localhost", "--tcp-port", "80"],
            text=True, capture_output=True, timeout=10, check=False,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertNotIn("SECRET_TEST", proc.stderr)

    def test_output_write_error(self):
        self.out.write_text("occupied", encoding="utf-8")
        proc, record = self.run_check(extra=("--output", str(self.out / "subdirectory")))
        self.assertEqual(proc.returncode, 3)
        self.assertTrue(record["overall_ok"])
        self.assertIn("no se pudo crear", proc.stderr)

    def test_exit_code_with_expected_http_status(self):
        proc, record = self.run_check(path="/unhealthy", extra=("--expect-status", "503"))
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(record["http"]["expected_status"], 503)


if __name__ == "__main__":
    unittest.main(verbosity=2)
