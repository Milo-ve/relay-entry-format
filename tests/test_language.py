"""R9: the optional `language` setting. English stays the default; Spanish covers the people-facing views.

Synthetic fixtures only. These tests pin both what is translated and what deliberately is not.
"""
from contextlib import redirect_stdout, redirect_stderr
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import io
import json
from pathlib import Path
import re
import string
import tempfile
import threading
import unittest
from urllib.parse import urlencode

from okf_icm import i18n, settings
from okf_icm.relay_cli import main
from okf_icm.routing import PROFILES
from okf_icm.storage import ContextError
from okf_icm.tasks import EXPERIENCE, PRINCIPLE, Tasks
from okf_icm.web import handler
from okf_icm.workspace import initialize

SRC = Path(__file__).resolve().parents[1] / "src" / "okf_icm"
STATUSES = ("ready", "blocked", "needs_review", "changes_requested", "awaiting_review", "accepted", "submitted")
# Keys that are built at run time from a code; each family must be complete.
FAMILIES = {"status.": STATUSES, "profile.": tuple(PROFILES), "freshness.": ("current", "changed"),
            "tl.": ("start", "refresh", "escalate", "submit", "reassign"),
            "web.kind_": ("auto", "transform", "draft", "diagnose", "design"), "web.risk_": ("standard", "low", "high")}


def placeholders(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


class Catalogue(unittest.TestCase):
    def test_both_languages_have_the_same_keys_and_placeholders(self):
        en, es = i18n.CATALOGUES["en"], i18n.CATALOGUES["es"]
        self.assertEqual(set(en), set(es))
        for key in en:
            self.assertEqual(placeholders(en[key]), placeholders(es[key]), key)
            self.assertTrue(es[key].strip(), key)

    def test_catalogue_text_is_safe_to_place_in_html_and_markdown(self):
        for language, catalogue in i18n.CATALOGUES.items():
            for key, text in catalogue.items():
                self.assertFalse(set(text) & set("<>&"), f"{language}:{key}")

    def test_spanish_is_actually_translated(self):
        en, es = i18n.CATALOGUES["en"], i18n.CATALOGUES["es"]
        same = [key for key in en if en[key] == es[key]]
        # Only entries that are pure placeholders may be identical in both languages.
        self.assertLessEqual(set(same), {"tl.actor", "tl.effort"})

    def test_every_key_used_in_the_code_exists_and_every_key_is_used(self):
        used, text = set(), ""
        for path in SRC.glob("*.py"):
            if path.name != "i18n.py":
                text += path.read_text(encoding="utf-8")
        used = set(re.findall(r"""\bt\(\s*["']([a-z_]+\.[a-z_0-9]+)["']""", text))
        used |= set(re.findall(r"""translator\([^)]*\)\(\s*["']([a-z_]+\.[a-z_0-9]+)["']""", text))
        used |= set(re.findall(r"""["'](?:card|guide|map|tl|web|st|snap)\.[a-z_0-9]+["']""", text))
        used = {x.strip("\"'") for x in used if not x.strip("\"'").endswith("_")}
        known = set(i18n.CATALOGUES["en"])
        self.assertEqual(sorted(x for x in used if x not in known), [])
        for key in known:
            self.assertTrue(key in used or any(key.startswith(prefix) for prefix in FAMILIES) or key == "self_recorded" or key == "effort",
                            f"unused key {key}")

    def test_runtime_built_keys_are_complete(self):
        for prefix, codes in FAMILIES.items():
            for code in codes:
                self.assertIn(prefix + code, i18n.CATALOGUES["en"])

    def test_english_interface_text_matches_the_packet_constants(self):
        self.assertEqual(i18n.CATALOGUES["en"]["web.experience"], EXPERIENCE)
        self.assertEqual(i18n.CATALOGUES["en"]["web.principle"], PRINCIPLE)

    def test_unknown_language_falls_back_to_english_and_unknown_codes_are_shown_as_they_are(self):
        self.assertEqual(i18n.translator("fr")("card.none"), "none")
        self.assertEqual(i18n.status_label("es", "something_new"), "something_new")
        self.assertEqual(i18n.profile_label("es", "standard"), "estándar")


class Project(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        initialize(self.root, "Language test")
        self.write("policy.md", "# Current\n149 MXN monthly.\n")
        self.tasks = Tasks(self.root)

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def setting(self, value):
        self.write(".context/relay/settings.json", json.dumps({"language": value}))

    def cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["--root", str(self.root), *args])
        return code, out.getvalue(), err.getvalue()

    def start(self, name="faq", **kwargs):
        defaults = dict(goal="Redactar preguntas frecuentes <b>", acceptance=["Cita la política"], selections=["policy.md"])
        return self.tasks.start(name, **{**defaults, **kwargs})

    def returned_and_accepted(self, name="faq"):
        self.write("work/result.md", "Resultado\n")
        self.write("work/evidence.md", "Comprobado\n")
        sub = self.tasks.submit(name, ["work/result.md"], ["work/evidence.md"], "Leí la política", "¿Y el IVA?", "Revisar")
        return self.tasks.review(name, sub["submission"]["submission_id"], "accept", "local-reviewer", "Correcto", external_ref="TICKET-1")


class SettingTests(Project):
    def test_default_is_english_and_absent_file_is_not_created(self):
        self.assertEqual(self.tasks.language(), "en")
        self.assertFalse((self.root / ".context/relay/settings.json").exists())

    def test_es_is_accepted(self):
        self.setting("es")
        self.assertEqual(self.tasks.language(), "es")

    def test_unknown_or_mistyped_language_is_refused_with_the_allowed_values(self):
        for bad in ("fr", "ES", "", None, 1, ["es"]):
            self.setting(bad)
            with self.assertRaises(ContextError) as caught:
                self.tasks.language()
            self.assertIn("language must be one of en, es", str(caught.exception))

    def test_language_is_not_a_control(self):
        self.start()
        self.setting("es")
        self.assertEqual(self.tasks.status("faq")["freshness"], "current")
        self.assertNotIn("language", (self.root / ".context/config.json").read_text())


class Guidance(Project):
    def test_next_step_follows_the_setting_and_keeps_the_codes_in_english(self):
        self.start()
        self.write("policy.md", "cambió\n")
        english = self.tasks.status("faq")
        self.setting("es")
        spanish = self.tasks.status("faq")
        self.assertEqual((spanish["status"], english["status"]), ("needs_review", "needs_review"))
        self.assertEqual(set(spanish), set(english))
        self.assertIn("Cambió desde la captura: policy.md", spanish["next_step"])
        self.assertIn(' refresh faq --note "qué cambió"`', spanish["next_step"])
        self.assertIn("Changed since the snapshot: policy.md", english["next_step"])

    def test_each_status_has_spanish_guidance_with_its_command(self):
        self.setting("es")
        self.start(blockers=["Falta el texto legal"])
        self.assertIn("Requisitos previos abiertos: Falta el texto legal", self.tasks.status("faq")["next_step"])
        self.tasks.refresh("faq", "resuelto", resolve=True)
        self.assertIn("Exporta el paquete con `relay", self.tasks.status("faq")["next_step"])
        self.assertIn(" context faq --out faq-context.md`", self.tasks.status("faq")["next_step"])
        accepted = self.returned_and_accepted()
        self.assertIn("Aceptada por local-reviewer (autodeclarado)", accepted["next_step"])
        self.assertIn("Referencia: TICKET-1 (registrada, no verificada)", accepted["next_step"])

    def test_cli_hints_and_batch_preview_follow_the_setting(self):
        self.start()
        self.write("policy.md", "cambió\n")
        self.setting("es")
        code, out, err = self.cli("list", "--stale", "--brief")
        self.assertEqual(code, 0)
        self.assertIn("tarea(s) cambiaron desde su captura", err)
        self.assertEqual([x["id"] for x in json.loads(out)], ["faq"])
        _, out, _ = self.cli("refresh", "--all-stale", "--note", "x")
        self.assertIn("No se escribió nada", json.loads(out)["next_step"])
        self.assertEqual(set(json.loads(out)), {"mode", "stale", "tasks", "failed", "next_step"})

    def test_library_errors_and_json_keys_stay_english(self):
        self.setting("es")
        self.start()
        code, out, err = self.cli("start", "faq", "--goal", "x", "--accept", "y")
        self.assertEqual(code, 2)
        self.assertIn("Task exists. Choose another ID", err)
        self.assertEqual(set(json.loads(self.cli("show", "faq")[1])) >= {"status", "freshness", "changed", "next_step"}, True)

    def test_failure_hint_after_a_refused_command_is_spanish(self):
        self.start()
        self.write("policy.md", "cambió\n")
        self.setting("es")
        code, _, err = self.cli("context", "faq")
        self.assertEqual(code, 2)
        self.assertIn("Cannot export context", err)  # library message: English by design
        self.assertIn("relay: next: Cambió desde la captura", err)


class Snapshot(Project):
    def test_spanish_snapshot_uses_lang_es_keeps_the_csp_and_has_no_script(self):
        from okf_icm.viz import export_html
        self.start()
        self.returned_and_accepted()
        english = export_html(self.tasks)
        self.setting("es")
        page = export_html(self.tasks)
        self.assertIn('<html lang="es">', page)
        self.assertIn('<html lang="en">', english)
        for text in ("Instantánea de Relay", "Mapa de conocimiento", "Tareas (1)", "Esta versión fue aceptada", "Aceptada por local-reviewer (autodeclarado)",
                     "Las comprobaciones son las que reportó quien entregó"):
            self.assertIn(text, page)
        self.assertNotIn("<script", page)
        self.assertRegex(page, r'content="default-src &#x27;none&#x27;; style-src &#x27;sha256-[A-Za-z0-9+/=]+&#x27;; base-uri &#x27;none&#x27;; form-action &#x27;none&#x27;"')
        self.assertIn("Redactar preguntas frecuentes &lt;b&gt;", page)  # people's text is untouched and escaped
        self.assertNotIn("Relay snapshot generated", page)
        self.assertNotIn("Instantánea", english)

    def test_history_labels_are_spanish_and_keep_the_batch_mark(self):
        from okf_icm.viz import timeline_model
        self.start()
        self.write("policy.md", "cambió\n")
        self.cli("refresh", "--all-stale", "--note", "x", "--apply", "--actor", "Ana")
        self.setting("es")
        labels = [e["label"] for e in timeline_model(self.tasks, "faq")["events"]]
        self.assertEqual(labels[0], "Tarea abierta · esfuerzo estándar")
        self.assertEqual(labels[1], "Contexto actualizado · actualización por lote · Ana (autodeclarado)")

    def test_knowledge_map_is_translated_but_bundle_values_are_shown_as_recorded(self):
        from okf_icm.viz import bundle_section
        text = bundle_section(self.tasks.ws, "es")
        self.assertIn("Todavía no hay conceptos de conocimiento", text)
        self.assertIn("<code>okf-icm knowledge add</code>", text)


class Card(Project):
    def setUp(self):
        super().setUp()
        self.start()
        self.returned_and_accepted()
        self.setting("es")

    def test_markdown_card_in_spanish(self):
        from okf_icm.card import render
        text = render(self.tasks, "faq", "md")
        for part in ("# Tarjeta de entrega:", "## Estado, en tres partes separadas", "- **Fuentes seleccionadas:** Vigentes",
                     "- **Aceptación:** Aceptada por local-reviewer (autodeclarado) · referencia: TICKET-1 (registrada, no verificada)",
                     "## Objetivo y criterios de aceptación", "## Personas (las escribe cada quien)", "| Fuente | Sección | Función | sha256 | Captura | Ahora |",
                     "Comprobaciones que reportó quien entregó (Relay no las verifica):", "Aceptada por local-reviewer (autodeclarado) el ",
                     "## Identificadores", "esfuerzo estándar"):
            self.assertIn(part, text)
        self.assertNotIn("Delivery card", text)
        self.assertIn("Leí la política", text)  # people's text untouched
        self.assertNotIn("relay refresh", text)  # still no operator commands

    def test_html_card_in_spanish_keeps_its_guarantees(self):
        from okf_icm.card import render
        page = render(self.tasks, "faq", "html")
        self.assertIn('<html lang="es">', page)
        for part in ("<title>Tarjeta de entrega · faq</title>", "Criterios de aceptación", "Responsable (lo escribe cada quien)", "Identificadores",
                     "El paquete también incluye 4 archivo(s) de control del proyecto."):
            self.assertIn(part, page)
        self.assertNotIn("<script", page)
        self.assertIn("Redactar preguntas frecuentes &lt;b&gt;", page)
        self.assertNotIn("<b>", page)

    def test_changed_inputs_are_called_out_in_spanish(self):
        from okf_icm.card import render
        self.write("policy.md", "cambió\n")
        text = render(self.tasks, "faq", "md")
        self.assertIn("Cambiaron desde la selección: policy.md", text)
        self.assertIn("La aceptación anterior ya no aplica: cambiaron las entradas", text)
        self.assertIn("**modificada**", text)

    def test_cli_card_follows_the_setting_and_stays_read_only(self):
        before = {p: p.read_bytes() for p in (self.root / ".context").rglob("*") if p.is_file()}
        code, out, _ = self.cli("card", "faq")
        self.assertEqual(code, 0)
        self.assertIn("Tarjeta de entrega", out)
        self.assertEqual({p: p.read_bytes() for p in (self.root / ".context").rglob("*") if p.is_file()}, before)


class Interface(Project):
    def setUp(self):
        super().setUp()
        self.start()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler(self.tasks))
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(lambda: (self.server.shutdown(), self.server.server_close()))

    def get(self, path):
        conn = HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        conn.request("GET", path)
        response = conn.getresponse()
        result = response.status, dict(response.getheaders()), response.read().decode()
        conn.close()
        return result

    @staticmethod
    def shape(headers):
        headers = dict(headers)
        headers["Content-Security-Policy"] = re.sub(r"nonce-[^']+", "nonce-N", headers["Content-Security-Policy"])
        for volatile in ("Date", "Content-Length"):
            headers.pop(volatile, None)
        return headers

    def test_pages_render_in_spanish_with_the_same_security_headers(self):
        english = {path: self.get(path) for path in ("/", "/tasks/faq", "/map")}
        self.setting("es")
        spanish = {path: self.get(path) for path in ("/", "/tasks/faq", "/map")}
        for path in english:
            self.assertEqual(spanish[path][0], 200)
            self.assertEqual(self.shape(spanish[path][1]), self.shape(english[path][1]), path)
            self.assertIn('<html lang="es">', spanish[path][2])
            self.assertIn("Saltar al contenido", spanish[path][2])
            self.assertIn("Mapa de conocimiento", spanish[path][2])
            self.assertNotIn("<script", spanish[path][2])
            self.assertIn('<html lang="en">', english[path][2])
        home, task, _ = spanish["/"][2], spanish["/tasks/faq"][2], None
        for text in ("Retoma el trabajo donde se quedó.", "Empieza con un resultado", "Abrir tarea", "lista para trabajar", "esfuerzo estándar", "Que lo decidan las reglas"):
            self.assertIn(text, home)
        for text in ("Entiende los límites", "Devuelve trabajo para revisión", "Revisa esta versión", "Adáptate a la evidencia nueva", "Historial de esta tarea",
                     "Fuentes: vigentes", "Descargar el contexto para el asistente", "Aún sin entregar", "Cita la política"):
            self.assertIn(text, task)
        self.assertIn("Redactar preguntas frecuentes &lt;b&gt;", task)
        self.assertEqual(self.get("/packet/faq")[2], self.tasks.context("faq"))  # the packet is never translated

    def test_changed_alert_and_error_pages_in_spanish(self):
        self.setting("es")
        self.write("policy.md", "cambió\n")
        self.assertIn("Hace falta revisar: policy.md.", self.get("/tasks/faq")[2])
        code, _, page = self.get("/nowhere")
        self.assertEqual(code, 404)
        self.assertIn("Página no encontrada", page)
        code, _, page = self.get("/packet/faq")
        self.assertEqual(code, 400)
        self.assertIn("Acción no disponible", page)
        self.assertIn("Cannot export context", page)  # library error text stays English

    def test_form_field_names_and_values_do_not_change_with_the_language(self):
        english = self.get("/tasks/faq")[2]
        self.setting("es")
        spanish = self.get("/tasks/faq")[2]
        names = lambda html: sorted(set(re.findall(r'name="([a-z_]+)"', html)))
        self.assertEqual(names(spanish), names(english))
        self.assertEqual(sorted(re.findall(r'<option value="([a-z_]+)"', spanish)), sorted(re.findall(r'<option value="([a-z_]+)"', english)))

    def test_a_broken_settings_file_is_reported_in_english_on_the_page(self):
        self.write(".context/relay/settings.json", json.dumps({"language": "fr"}))
        code, _, page = self.get("/")
        self.assertEqual(code, 400)
        self.assertIn("language must be one of en, es", page)
        self.assertIn('<html lang="en">', page)

    def test_posting_in_spanish_still_works(self):
        self.setting("es")
        _, _, html = self.get("/tasks/faq")
        token = re.search(r'name="csrf" value="([^"]+)"', html)[1]
        conn = HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        body = urlencode({"csrf": token, "revision": "1", "note": "Cambió el precio"}).encode()
        conn.request("POST", "/refresh/faq", body=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
        self.assertEqual(conn.getresponse().status, 303)
        conn.close()
        self.assertEqual(self.tasks.load("faq")["events"][-1]["note"], "Cambió el precio")


if __name__ == "__main__":
    unittest.main()
