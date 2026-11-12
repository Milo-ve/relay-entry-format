"""HTTP-level tests for the local UI; no browser or model credentials required."""
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
import re
import tempfile
import threading
import unittest
from urllib.parse import urlencode

from okf_icm.tasks import Tasks
from okf_icm.web import handler
from okf_icm.workspace import initialize


class WebCase(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        initialize(self.root, "HTTP test")
        (self.root / "source.md").write_text("149 MXN monthly.")
        self.tasks = Tasks(self.root)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler(self.tasks))
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown()
        self.server.server_close()

    def request(self, method, path, data=None, headers=None):
        conn = HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        body = urlencode(data).encode() if data is not None else None
        request_headers = {"Content-Type": "application/x-www-form-urlencoded"} if data is not None else {}
        request_headers.update(headers or {})
        conn.request(method, path, body=body, headers=request_headers)
        response = conn.getresponse()
        result = response.status, dict(response.getheaders()), response.read().decode()
        conn.close()
        return result

    def token(self, html):
        return re.search(r'name="csrf" value="([^"]+)"', html)[1]

    def start(self):
        code, headers, html = self.request("GET", "/")
        self.assertEqual(code, 200)
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertEqual(headers["Cache-Control"], "no-store")
        data = {"csrf": self.token(html), "id": "faq", "goal": "FAQ <script>alert(1)</script>",
                "acceptance": "Source-backed", "sources": "source.md", "kind": "draft", "risk": "standard", "owner": "worker", "reviewer": "milo"}
        self.assertEqual(self.request("POST", "/start", data)[0], 303)
        return self.request("GET", "/tasks/faq")[2]

    def test_web_create_export_submit_review_roundtrip(self):
        html = self.start()
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>", html)
        code, headers, packet = self.request("GET", "/packet/faq")
        self.assertEqual(code, 200)
        self.assertIn("attachment", headers["Content-Disposition"])
        self.assertIn("149 MXN", packet)
        data = {"csrf": self.token(html), "revision": "1", "result": "149 MXN; source.md", "evidence": "Compared fixture price: matches", "checks": "Compared source", "next": "Review"}
        self.assertEqual(self.request("POST", "/submit/faq", data)[0], 303)
        status = self.tasks.status("faq")
        self.assertEqual(status["status"], "awaiting_review")
        html = self.request("GET", "/tasks/faq")[2]
        data = {"csrf": self.token(html), "revision": str(status["revision"]), "submission": status["submission"]["submission_id"], "actor": "milo", "decision": "accept", "note": "Compared with current source"}
        self.assertEqual(self.request("POST", "/review/faq", data)[0], 303)
        self.assertEqual(self.tasks.status("faq")["status"], "accepted")

    def test_host_origin_and_csrf_checks(self):
        self.assertEqual(self.request("GET", "/", headers={"Host": "attacker.example"})[0], 403)
        html = self.start()
        data = {"csrf": self.token(html), "revision": "1", "note": "test"}
        self.assertEqual(self.request("POST", "/refresh/faq", data, {"Origin": "https://attacker.example"})[0], 400)
        data["csrf"] = "invalid"
        self.assertEqual(self.request("POST", "/refresh/faq", data)[0], 400)
        self.assertEqual(self.tasks.load("faq")["revision"], 1)

    def test_stale_form_does_not_create_result_files(self):
        html = self.start()
        self.tasks.refresh("faq", "New version")
        data = {"csrf": self.token(html), "revision": "1", "result": "Draft", "evidence": "Checks", "checks": "Checked", "next": "Review"}
        code, _, body = self.request("POST", "/submit/faq", data)
        self.assertEqual(code, 400)
        self.assertIn("Reload", body)
        self.assertFalse((self.root / "deliverables").exists())


    def test_optional_name_is_recorded_only_when_typed(self):
        html = self.start()
        self.assertIn('name="actor"', html)
        token = self.token(html)
        self.assertEqual(self.request("POST", "/refresh/faq", {"csrf": token, "revision": "1", "note": "Anonymous", "actor": "  "})[0], 303)
        self.assertEqual(self.request("POST", "/refresh/faq", {"csrf": token, "revision": "2", "note": "Named", "actor": " ana "})[0], 303)
        events = self.tasks.load("faq")["events"]
        self.assertNotIn("actor", events[-2])
        self.assertEqual(events[-1]["actor"], "ana")

    def test_review_form_offers_an_optional_reference(self):
        html = self.start()
        data = {"csrf": self.token(html), "revision": "1", "result": "149 MXN", "evidence": "Compared", "checks": "Compared", "next": "Review"}
        self.assertEqual(self.request("POST", "/submit/faq", data)[0], 303)
        status = self.tasks.status("faq")
        html = self.request("GET", "/tasks/faq")[2]
        self.assertIn('name="external_ref"', html)
        data = {"csrf": self.token(html), "revision": str(status["revision"]), "submission": status["submission"]["submission_id"],
                "actor": "milo", "decision": "accept", "note": "Ok", "external_ref": " TICKET-9 "}
        self.assertEqual(self.request("POST", "/review/faq", data)[0], 303)
        self.assertEqual(self.tasks.status("faq")["review"]["external_ref"], "TICKET-9")
        self.assertIn("TICKET-9 (recorded, not verified)", self.request("GET", "/tasks/faq")[2])

if __name__ == "__main__":
    unittest.main()
