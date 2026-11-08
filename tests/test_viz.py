"""Visualization tests: synthetic data only; no browser, network or model."""
import base64
from contextlib import redirect_stderr, redirect_stdout
import io
import hashlib
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import re
import tempfile
import threading
import unittest

from okf_icm import knowledge as k
from okf_icm import viz
from okf_icm.relay_cli import main as relay_main
from okf_icm.storage import atomic_write
from okf_icm.tasks import Tasks
from okf_icm.web import handler
from okf_icm.workspace import Workspace, initialize


def concept(root, cid, title, body, **meta):
    meta = {"type": "Decision", "title": title, **meta}
    atomic_write(root / ".context/knowledge" / (cid + ".md"), k.serialize(meta, body))


class Fixture(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        initialize(self.root, "Viz test")
        self.ws = Workspace(self.root)
        concept(self.root, "a/one", "One <b>bold</b>", "See [two](../b/two.md), [missing](nope.md), [web](https://example.org/x) and [self](one.md).\n",
                verified=[{"by": "human:milo", "at": "2026-01-01T00:00:00+00:00"}], stale_after="2099-01-01T00:00:00+00:00", status="stable")
        concept(self.root, "b/two", "Two", "Back to [one](../a/one.md). `[code](../a/one.md)`\n```\n[fenced](../a/one.md)\n```\n",
                verified=[{"by": "process:check", "at": "2026-01-01T00:00:00+00:00"}], stale_after="2000-01-01T00:00:00+00:00", status="draft")
        concept(self.root, "c", "Three", "Leaves [out](../../outside.md).\n", status="deprecated")
        atomic_write(self.root / "source.md", "149 MXN monthly. SECRET-SOURCE-TEXT\n")
        self.tasks = Tasks(self.root)

    def start(self, name="faq"):
        return self.tasks.start(name, "FAQ <script>x</script>", ["Source-backed"], ["source.md"], kind="draft", reviewer="milo")


class VizCase(Fixture):
    # -- knowledge map
    def test_bundle_edges_ignore_unresolved_external_self_and_code(self):
        model = viz.bundle_model(self.ws)
        self.assertEqual({n["id"] for n in model["nodes"]}, {"a/one", "b/two", "c"})
        self.assertEqual(sorted(model["edges"]), [("a/one", "b/two"), ("b/two", "a/one")])

    def test_bundle_svg_escapes_and_avoids_script_and_style_attributes(self):
        html = viz.bundle_section(self.ws)
        self.assertIn("&lt;b&gt;bold&lt;/b&gt;", html)
        self.assertNotIn("<b>bold", html)
        self.assertNotIn("<script", html)
        self.assertNotRegex(html, r"\sstyle=")
        self.assertIn("1 unresolved link", html)
        self.assertIn("1 link(s) leaving the bundle", html)
        for shape in ("<circle", "<rect", "<polygon"):
            self.assertIn(shape, html)
        self.assertIn("stale", html)

    def test_invalid_concept_is_reported_not_hidden(self):
        atomic_write(self.root / ".context/knowledge/bad.md", "---\ntype: X\nstatus: nonsense\n---\nbody\n")
        html = viz.bundle_section(self.ws)
        self.assertIn("invalid and not drawn", html)
        self.assertIn("status must be draft", html)

    def test_empty_bundle_says_so(self):
        with tempfile.TemporaryDirectory() as temp:
            initialize(Path(temp), "Empty")
            self.assertIn("No knowledge concepts yet", viz.bundle_section(Workspace(Path(temp))))

    def test_node_cap_is_disclosed(self):
        for i in range(viz.MAX_NODES + 3):
            concept(self.root, f"bulk/n{i:03d}", f"N{i}", "x\n")
        html = viz.bundle_section(self.ws)
        self.assertIn(f"first {viz.MAX_NODES} concepts", html)
        self.assertIn("bulk/n102", html)  # every concept stays in the table

    # -- timeline
    def test_timeline_tracks_review_and_supersession(self):
        self.start()
        atomic_write(self.root / "faq.md", "answer\n")
        atomic_write(self.root / "ev.md", "compared\n")
        s = self.tasks.submit("faq", ["faq.md"], ["ev.md"], "Compared", "", "Review")
        self.tasks.review("faq", s["submission"]["submission_id"], "accept", "milo", "ok")
        html = viz.timeline_section(self.tasks, "faq")
        self.assertIn("Accepted by milo (self-recorded)", html)
        self.assertIn("Accepted this version", html)
        self.assertNotIn("superseded by a later refresh", html.split("<svg")[1].split("</svg>")[0])
        # Source changes: the earlier acceptance must no longer read as current.
        atomic_write(self.root / "source.md", "179 MXN\n")
        self.assertIn("Earlier acceptance no longer applies", viz.timeline_section(self.tasks, "faq"))
        # Refresh: old submit/review are shown as superseded, acceptance is gone.
        self.tasks.refresh("faq", "price changed")
        html = viz.timeline_section(self.tasks, "faq")
        # start, submit and review all predate the refresh; only the refresh is current.
        self.assertEqual(html.split("<svg")[1].split("</svg>")[0].count("superseded by a later refresh"), 3)
        self.assertIn("Not accepted", html)
        self.assertIn("Not returned yet", html)

    def test_timeline_escapes_task_text_and_states_checks_are_unverified(self):
        self.start()
        html = viz.timeline_section(self.tasks, "faq")
        self.assertNotIn("<script", html)
        self.assertIn("Relay does not verify them", html)

    # -- export
    def test_export_is_self_contained_and_pinned_by_hash(self):
        self.start()
        html = viz.export_html(self.tasks)
        self.assertNotIn("<script", html)
        self.assertNotIn("http://", html.replace("http://www.w3.org/2000/svg", "").replace("http-equiv", ""))
        self.assertNotIn("SECRET-SOURCE-TEXT", html)
        self.assertNotIn("149 MXN", html)
        css = re.search(r"<style>(.*?)</style>", html, re.S)[1]
        digest = base64.b64encode(hashlib.sha256(css.encode()).digest()).decode()
        self.assertIn(f"style-src &#x27;sha256-{digest}&#x27;", html)
        self.assertIn("point-in-time copy", html)
        self.assertIn("FAQ &lt;script&gt;x&lt;/script&gt;", html)

    def test_export_reports_unreadable_task_instead_of_dropping_it(self):
        self.start()
        self.start("other")
        for packet in (self.root / ".context/relay/tasks/other/packets").glob("*.json"):
            packet.write_text(packet.read_text().replace("Source-backed", "Tampered"))
        html = viz.export_html(self.tasks)
        self.assertIn("could not be read and is not shown", html)
        self.assertIn("FAQ &lt;script&gt;", html)

    def test_cli_export_refuses_to_overwrite(self):
        self.start()
        out = self.root / "snapshot.html"
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(relay_main(["--root", str(self.root), "export-html", "--out", str(out)]), 0)
            first = out.read_text()
            self.assertEqual(relay_main(["--root", str(self.root), "export-html", "--out", str(out)]), 2)
        self.assertEqual(out.read_text(), first)


class VizWebCase(Fixture):
    def setUp(self):
        super().setUp()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler(self.tasks))
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown()
        self.server.server_close()

    def get(self, path, headers=None):
        conn = HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        conn.request("GET", path, headers=headers or {})
        r = conn.getresponse()
        out = r.status, dict(r.getheaders()), r.read().decode()
        conn.close()
        return out

    def test_map_and_task_pages_keep_the_script_free_csp(self):
        self.start()
        for path in ("/map", "/tasks/faq"):
            code, headers, html = self.get(path)
            self.assertEqual(code, 200, path)
            csp = headers["Content-Security-Policy"]
            self.assertIn("default-src 'none'", csp)
            self.assertNotIn("script-src", csp)
            self.assertNotIn("unsafe-inline", csp)
            self.assertNotIn("<script", html)
            self.assertNotRegex(html, r"\sstyle=")
        self.assertIn("<svg", self.get("/map")[2])
        self.assertIn("History of this task", self.get("/tasks/faq")[2])

    def test_map_enforces_host_check(self):
        self.assertEqual(self.get("/map", {"Host": "attacker.example"})[0], 403)

    def test_corrupt_bundle_does_not_crash_the_server(self):
        atomic_write(self.root / ".context/knowledge/broken.md", "---\n: : :\n---\n")
        self.assertEqual(self.get("/map")[0], 200)


if __name__ == "__main__":
    unittest.main()
