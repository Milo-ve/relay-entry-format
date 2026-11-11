"""Display text for the people-facing views, in English (default) and Spanish.

Scope. Only text Relay itself writes for people is translated: the local interface, the knowledge
map and task history, the exported snapshot, the delivery card, next-step guidance and its status
labels. These stay English on purpose: library error messages, CLI option names, JSON keys, status
and effort codes in JSON, packet contents, event names on disk, and anything people typed (goals,
criteria, notes, names). Values taken from a knowledge bundle (type, lifecycle, trust, freshness)
are shown as the bundle recorded them.

Each entry is an (English, Spanish) pair, so both languages always have the same keys. A test also
checks that both texts use the same placeholders. Catalogue text is trusted and written to be safe in
HTML and Markdown (no angle brackets or ampersands); callers escape the values they pass in.
Command lines inside the text (`relay refresh ...`) keep their English words, because the commands do.
"""
from __future__ import annotations

LANGUAGES = ("en", "es")
DEFAULT = "en"

_PAIRS: dict[str, tuple[str, str]] = {
    # ---------------------------------------------------------------- status and effort labels
    "status.ready": ("ready", "lista para trabajar"),
    "status.blocked": ("blocked", "bloqueada"),
    "status.needs_review": ("needs_review", "requiere revisión"),
    "status.changes_requested": ("changes_requested", "cambios solicitados"),
    "status.awaiting_review": ("awaiting_review", "esperando revisión"),
    "status.accepted": ("accepted", "aceptada"),
    "status.submitted": ("submitted", "entregada"),
    "profile.direct": ("direct", "directo"),
    "profile.standard": ("standard", "estándar"),
    "profile.investigative": ("investigative", "investigativo"),
    "profile.clarify": ("clarify", "aclaración"),
    "effort": ("{profile} effort", "esfuerzo {profile}"),
    "freshness.current": ("current", "vigentes"),
    "freshness.changed": ("changed", "modificadas"),
    "self_recorded": ("(self-recorded)", "(autodeclarado)"),

    # ---------------------------------------------------------------- next-step guidance
    "guide.more": ("(+{n} more)", "(+{n} más)"),
    "guide.needs_review": (
        "Changed since the snapshot: {changed}. Run `{relay} refresh {task} --note \"what changed\"` to take a new snapshot. "
        "That clears the current submission and acceptance and keeps the history. Then reassess the work the change affects.",
        "Cambió desde la captura: {changed}. Ejecuta `{relay} refresh {task} --note \"qué cambió\"` para tomar una captura nueva. "
        "Eso borra la entrega y la aceptación actuales y conserva el historial. Después, revisa de nuevo el trabajo que afecta el cambio."),
    "guide.also_open": (" Prerequisites are also still open: {blockers}.", " Además siguen abiertos estos requisitos previos: {blockers}."),
    "guide.blocked": (
        "Open prerequisites: {blockers}. Resolve them outside Relay, then run `{relay} refresh {task} --resolve --note \"what was resolved\"`. "
        "--resolve records that you resolved them; Relay does not check.",
        "Requisitos previos abiertos: {blockers}. Resuélvelos fuera de Relay y luego ejecuta "
        "`{relay} refresh {task} --resolve --note \"qué se resolvió\"`. --resolve registra que tú los resolviste; Relay no lo comprueba."),
    "guide.ready": (
        "Export the packet with `{relay} context {task} --out {task}-context.md` and work in your assistant. "
        "Save the result and the checks you actually ran as separate files, then run {submit}.",
        "Exporta el paquete con `{relay} context {task} --out {task}-context.md` y trabaja en tu asistente. "
        "Guarda el resultado y las comprobaciones que realmente hiciste como archivos separados, y luego ejecuta {submit}."),
    "guide.awaiting": (
        "Waiting for {reviewer} to review this exact version: "
        "`{relay} review {task} --submission {sid} --decision accept|request_changes --actor {reviewer} --note \"...\"`. "
        "Editing the result, the evidence or a source before then returns the task to needs_review.",
        "Esperando que {reviewer} revise exactamente esta versión: "
        "`{relay} review {task} --submission {sid} --decision accept|request_changes --actor {reviewer} --note \"...\"`. "
        "Si antes se edita el resultado, la evidencia o una fuente, la tarea vuelve a needs_review."),
    "guide.changes_requested": (
        "Changes were requested; read the review note in this output. Revise the result and evidence, "
        "then run `{relay} refresh {task} --note \"what you revised\"` (editing the files changes the submitted version) and {submit} again.",
        "Se solicitaron cambios; lee la nota de revisión en esta salida. Corrige el resultado y la evidencia, "
        "luego ejecuta `{relay} refresh {task} --note \"qué corregiste\"` (editar los archivos cambia la versión entregada) y vuelve a ejecutar {submit}."),
    "guide.accepted": (
        "Accepted by {actor} (self-recorded) for submission {sid}.{reference} "
        "The acceptance covers only this version: if a source, the result or the evidence changes, the task returns to needs_review. "
        "Folding the result into a canonical source is a separate step that Relay does not perform.",
        "Aceptada por {actor} (autodeclarado) para la entrega {sid}.{reference} "
        "La aceptación cubre solo esta versión: si cambia una fuente, el resultado o la evidencia, la tarea vuelve a needs_review. "
        "Incorporar el resultado a una fuente canónica es un paso aparte que Relay no realiza."),
    "guide.reference": (" Reference: {ref} (recorded, not verified).", " Referencia: {ref} (registrada, no verificada)."),
    "guide.submitted": (
        "Submitted. This task does not require review, so nothing here records acceptance.",
        "Entregada. Esta tarea no requiere revisión, así que aquí no se registra ninguna aceptación."),
    "guide.after_context": (
        "Packet exported. Work in your assistant. Save the result and the checks you actually ran as separate files, "
        "outside .context and not among the selected inputs, then run {submit}.",
        "Paquete exportado. Trabaja en tu asistente. Guarda el resultado y las comprobaciones que realmente hiciste como archivos separados, "
        "fuera de .context y que no sean parte de las entradas seleccionadas, y luego ejecuta {submit}."),
    "guide.stale": (
        "{count} task(s) changed since their snapshot. `{relay} show TASK` explains one. After a shared source changed, "
        "`{relay} refresh --all-stale --note \"what changed\"` previews refreshing all of them and writes nothing; "
        "add --apply to do it. A refresh clears each task's submission and acceptance, so reassess the work first.",
        "{count} tarea(s) cambiaron desde su captura. `{relay} show TASK` explica una. Si cambió una fuente compartida, "
        "`{relay} refresh --all-stale --note \"qué cambió\"` muestra qué pasaría al actualizarlas todas y no escribe nada; "
        "agrega --apply para hacerlo. Actualizar borra la entrega y la aceptación de cada tarea, así que revisa primero el trabajo."),
    "guide.batch_apply": (
        "Nothing was written. Run the same command with --apply to refresh the tasks listed under `tasks`. "
        "Each loses its current submission and acceptance; history is kept. No review is created.",
        "No se escribió nada. Ejecuta el mismo comando con --apply para actualizar las tareas de `tasks`. "
        "Cada una pierde su entrega y su aceptación actuales; el historial se conserva. No se crea ninguna revisión."),
    "guide.batch_nothing": ("Nothing was written.", "No se escribió nada."),
    "guide.batch_none": ("No task has changed inputs.", "Ninguna tarea tiene entradas modificadas."),

    # ---------------------------------------------------------------- local interface
    "web.skip": ("Skip to content", "Saltar al contenido"),
    "web.brand_suffix": (" / local workspace", " / espacio de trabajo local"),
    "web.nav_map": ("Knowledge map", "Mapa de conocimiento"),
    "web.tag1": ("Portable context.", "Contexto portátil."),
    "web.tag2": ("Proportional effort.", "Esfuerzo proporcional."),
    "web.footer": (
        "Local trusted-user prototype. Reviewer identities are self-recorded. Assistant compute settings are advisory. No organization authentication or remote sharing.",
        "Prototipo local para personas de confianza. Las identidades de quien revisa las escribe cada quien. Los ajustes de cómputo del asistente son solo una recomendación. "
        "Sin autenticación de organización ni uso compartido remoto."),
    "web.experience": (
        "Open the task. Understand its boundaries. Continue with your preferred assistant. Return reviewable work.",
        "Abre la tarea. Entiende sus límites. Continúa con el asistente que prefieras. Devuelve trabajo que se pueda revisar."),
    "web.principle": (
        "Use the least total effort that satisfies the task’s requirements, and increase effort when evidence shows it is needed.",
        "Usa el menor esfuerzo total que cumpla los requisitos de la tarea, y auméntalo cuando la evidencia muestre que hace falta."),
    "web.home_title": ("Your work", "Tu trabajo"),
    "web.steps": ("OPEN → UNDERSTAND → CONTINUE → RETURN", "ABRIR → ENTENDER → CONTINUAR → DEVOLVER"),
    "web.home_h1": ("Pick up where work left off.", "Retoma el trabajo donde se quedó."),
    "web.no_tasks": ("No tasks yet. Open a task to prepare its first handoff.", "Todavía no hay tareas. Abre una para preparar su primera entrega."),
    "web.start_h2": ("Start with an outcome", "Empieza con un resultado"),
        "web.f_id": ("Task ID", "ID de la tarea"),
    "web.f_goal": ("What should this task achieve?", "¿Qué debe lograr esta tarea?"),
    "web.f_acceptance": ("What will make the result acceptable? One criterion per line.", "¿Qué hará aceptable el resultado? Un criterio por línea."),
    "web.f_sources": ("Source paths, one per line", "Rutas de las fuentes, una por línea"),
    "web.sources_hint": (
        "Use paths relative to this project. Only selected sources and project controls enter the packet.",
        "Usa rutas relativas a este proyecto. Solo las fuentes seleccionadas y los controles del proyecto entran al paquete."),
    "web.f_kind": ("Kind of work", "Tipo de trabajo"),
    "web.kind_auto": ("Let the rules assess it", "Que lo decidan las reglas"),
    "web.kind_transform": ("Specified transformation", "Transformación especificada"),
    "web.kind_draft": ("Draft or synthesis", "Borrador o síntesis"),
    "web.kind_diagnose": ("Diagnosis", "Diagnóstico"),
    "web.kind_design": ("Open-ended design", "Diseño abierto"),
    "web.f_risk": ("Consequences", "Consecuencias"),
    "web.risk_standard": ("Standard", "Normales"),
    "web.risk_low": ("Low and reversible", "Bajas y reversibles"),
    "web.risk_high": ("High / consequential", "Altas / importantes"),
    "web.f_owner": ("Task owner", "Responsable de la tarea"),
    "web.f_reviewer": ("Reviewer", "Quien revisa"),
    "web.open_task": ("Open task", "Abrir tarea"),
    "web.map_title": ("Knowledge map", "Mapa de conocimiento"),
    "web.all_tasks": ("← All tasks", "← Todas las tareas"),
    "web.map_intro": (
        "Concepts in {code} and the links between them. Trust and freshness are the bundle's own recorded signals; Relay does not verify them.",
        "Conceptos de {code} y los vínculos entre ellos. La confianza y la vigencia son las señales que el propio paquete registró; Relay no las verifica."),
    "web.changed_alert": (
        "Review needed: {paths}. Refresh the context and reassess affected work.",
        "Hace falta revisar: {paths}. Actualiza el contexto y revisa de nuevo el trabajo afectado."),
    "web.f_result": ("Your deliverable", "Tu entregable"),
    "web.f_evidence": ("Actual evidence / observed results", "Evidencia real / resultados observados"),
    "web.f_checks": ("What did you check?", "¿Qué comprobaste?"),
    "web.f_questions": ("Open questions", "Preguntas abiertas"),
    "web.f_next": ("Next action", "Siguiente acción"),
    "web.f_next_default": ("Review this submission against the acceptance criteria.", "Revisar esta entrega contra los criterios de aceptación."),
    "web.f_actor": ("Your name (optional, self-recorded)", "Tu nombre (opcional, lo escribes tú)"),
    "web.b_return": ("Return reviewable work", "Devolver trabajo para revisión"),
    "web.review_first": ("Return a result before recording a review.", "Devuelve un resultado antes de registrar una revisión."),
    "web.f_reviewer_actor": ("Reviewer (self-recorded)", "Quien revisa (lo escribe cada quien)"),
    "web.f_external_ref": (
        "Reference to an approval kept elsewhere (optional; recorded, not checked)",
        "Referencia a una aprobación guardada en otro lugar (opcional; se registra, no se comprueba)"),
    "web.f_review_note": ("Review rationale", "Motivo de la revisión"),
    "web.f_decision": ("Decision", "Decisión"),
    "web.accept_option": ("Accept this version", "Aceptar esta versión"),
    "web.changes_option": ("Request changes", "Solicitar cambios"),
    "web.b_review": ("Record review", "Registrar revisión"),
    "web.f_refresh_note": ("What changed or was resolved?", "¿Qué cambió o qué se resolvió?"),
    "web.f_resolved": ("I resolved the listed prerequisites", "Resolví los requisitos previos listados"),
    "web.b_refresh": ("Refresh context", "Actualizar contexto"),
    "web.f_escalate_note": ("Evidence requiring more effort", "Evidencia que exige más esfuerzo"),
    "web.b_escalate": ("Escalate effort", "Subir el esfuerzo"),
    "web.h_boundaries": ("Understand the boundaries", "Entiende los límites"),
    "web.people": ("Owner: {owner} · Reviewer: {reviewer}", "Responsable: {owner} · Revisión: {reviewer}"),
    "web.h_acceptance": ("Acceptance", "Aceptación"),
    "web.h_sources": ("Selected sources", "Fuentes seleccionadas"),
    "web.blockers": ("Blockers: {blockers}", "Bloqueos: {blockers}"),
    "web.no_blockers": ("None recorded", "Ninguno registrado"),
    "web.download": ("Download assistant context", "Descargar el contexto para el asistente"),
    "web.s_effort": ("Effort decision", "Decisión de esfuerzo"),
    "web.h_return": ("Return reviewable work", "Devuelve trabajo para revisión"),
    "web.return_hint": (
        "The text below is saved as versioned result and evidence files. Describe checks you actually performed.",
        "El texto de abajo se guarda como archivos de resultado y de evidencia con versión. Describe las comprobaciones que realmente hiciste."),
    "web.h_review": ("Review this version", "Revisa esta versión"),
    "web.s_record": ("Submission and review record", "Registro de entrega y revisión"),
    "web.h_adapt": ("Adapt to new evidence", "Adáptate a la evidencia nueva"),
    "web.s_more_effort": ("Need more effort?", "¿Hace falta más esfuerzo?"),
    "web.h_history": ("History of this task", "Historial de esta tarea"),
    "web.sources_state": ("Sources: {freshness}", "Fuentes: {freshness}"),
    "web.not_found": ("Page not found", "Página no encontrada"),
    "web.to_tasks": ("Return to tasks", "Volver a las tareas"),
    "web.unavailable": ("Action unavailable", "Acción no disponible"),
    "web.not_saved": ("Could not save", "No se pudo guardar"),
    "web.not_saved_h1": ("Could not save this action", "No se pudo guardar esta acción"),
    "web.not_saved_hint": (
        "Go back to retain your form, or reload the task to use its current version.",
        "Regresa para conservar tu formulario, o recarga la tarea para usar su versión actual."),

    # ---------------------------------------------------------------- knowledge map
    "map.title": ("Knowledge map", "Mapa de conocimiento"),
    "map.desc": (
        "{n} concepts and {links} links. {shape} The table below lists every concept.",
        "{n} conceptos y {links} vínculos. {shape} La tabla de abajo lista todos los conceptos."),
    "map.shape": (
        "Shape = lifecycle (circle stable, square draft, diamond deprecated). Fill = trust. Dashed outline = stale.",
        "Forma = ciclo de vida (círculo estable, cuadrado borrador, rombo obsoleto). Relleno = confianza. Contorno punteado = desactualizado."),
    "map.node": (
        "{title} ({id}): {type}, {status}, {trust}, freshness {freshness}",
        "{title} ({id}): {type}, {status}, {trust}, vigencia {freshness}"),
    "map.l_human": ("Stable, human-reviewed", "Estable, revisado por una persona"),
    "map.l_machine": ("Stable, machine-confirmed", "Estable, confirmado por máquina"),
    "map.l_none": ("Stable, unverified", "Estable, sin verificar"),
    "map.l_draft": ("Draft", "Borrador"),
    "map.l_deprecated": ("Deprecated", "Obsoleto"),
    "map.l_stale": ("Stale (dashed)", "Desactualizado (punteado)"),
    "map.caption": (
        "Links are out / in. Trust labels are the bundle's own recorded claims; Relay does not verify them.",
        "Los vínculos son salientes / entrantes. Las etiquetas de confianza son afirmaciones que el propio paquete registró; Relay no las verifica."),
    "map.h_concept": ("Concept", "Concepto"),
    "map.h_title": ("Title", "Título"),
    "map.h_type": ("Type", "Tipo"),
    "map.h_status": ("Status", "Estado"),
    "map.h_trust": ("Trust", "Confianza"),
    "map.h_freshness": ("Freshness", "Vigencia"),
    "map.h_links": ("Links", "Vínculos"),
    "map.empty": ("No knowledge concepts yet. Add one with {cmd}.", "Todavía no hay conceptos de conocimiento. Agrega uno con {cmd}."),
    "map.truncated": (
        "The map draws the first {max} concepts; {cut} more appear only in the table.",
        "El mapa dibuja los primeros {max} conceptos; {cut} más aparecen solo en la tabla."),
    "map.invalid": ("{n} concept(s) are invalid and not drawn:", "{n} concepto(s) no son válidos y no se dibujan:"),
    "map.unresolved": (
        "{unresolved} unresolved link(s) (allowed by OKF) and {leaving} link(s) leaving the bundle are not drawn.",
        "{unresolved} vínculo(s) sin resolver (permitidos por OKF) y {leaving} vínculo(s) que salen del paquete no se dibujan."),

    # ---------------------------------------------------------------- task history
    "tl.start": ("Task opened", "Tarea abierta"),
    "tl.refresh": ("Context refreshed", "Contexto actualizado"),
    "tl.escalate": ("Effort escalated", "Esfuerzo aumentado"),
    "tl.submit": ("Work returned", "Trabajo devuelto"),
    "tl.reassign": ("Owner or reviewer reassigned", "Responsable o revisión reasignados"),
    "tl.accept": ("Accepted this version", "Esta versión fue aceptada"),
    "tl.changes": ("Changes requested", "Cambios solicitados"),
    "tl.actor": ("{label} · {actor} {sr}", "{label} · {actor} {sr}"),
    "tl.ref": (" · reference: {ref} (recorded, not verified)", " · referencia: {ref} (registrada, no verificada)"),
    "tl.effort": (" · {effort}", " · {effort}"),
    "tl.reassigned": (" · reviewer {reviewer}, owner {owner}", " · revisión {reviewer}, responsable {owner}"),
    "tl.batch": (" · batch refresh", " · actualización por lote"),
    "tl.superseded": (" · superseded by a later refresh", " · reemplazado por una actualización posterior"),
    "tl.at": ("{label} at {at}", "{label} el {at}"),
    "tl.superseded_short": (" (superseded)", " (reemplazado)"),
    "tl.title": ("Task history", "Historial de la tarea"),
    "tl.note": (
        "{n} context packet version(s) recorded. Faded events were superseded by a later refresh and no longer count toward the current version. "
        "Marks show recorded events, not proof that checks were correct.",
        "{n} versión(es) del paquete de contexto registradas. Los eventos atenuados fueron reemplazados por una actualización posterior y ya no cuentan para la versión actual. "
        "Las marcas muestran eventos registrados, no prueban que las comprobaciones fueran correctas."),
    "st.sources_ok": ("Current", "Vigentes"),
    "st.sources_changed": ("Changed since selected: {paths}", "Cambiaron desde la selección: {paths}"),
    "st.work_yes": ("Returned for this version", "Entregado para esta versión"),
    "st.work_no": ("Not returned yet", "Aún sin entregar"),
    "st.accepted": ("Accepted by {actor} (self-recorded)", "Aceptada por {actor} (autodeclarado)"),
    "st.accept_void": ("Earlier acceptance no longer applies: inputs changed", "La aceptación anterior ya no aplica: cambiaron las entradas"),
    "st.changes": ("Changes requested", "Cambios solicitados"),
    "st.blocked": ("Blocked: {blockers}", "Bloqueada: {blockers}"),
    "st.not_accepted": ("Not accepted", "Sin aceptar"),
    "st.h_sources": ("Selected sources", "Fuentes seleccionadas"),
    "st.h_work": ("Work and reported checks", "Trabajo y comprobaciones reportadas"),
    "st.checks_note": (
        "Checks are as reported by the submitter; Relay does not verify them.",
        "Las comprobaciones son las que reportó quien entregó; Relay no las verifica."),
    "st.h_acceptance": ("Acceptance", "Aceptación"),

    # ---------------------------------------------------------------- exported snapshot
    "snap.title": ("{project} · Relay snapshot", "{project} · Instantánea de Relay"),
    "snap.intro": (
        "Relay snapshot generated {stamp}. It is a point-in-time copy, not a live view. It lists goals, acceptance state, "
        "owners, reviewers and recorded events; it contains no source, packet or deliverable contents. Names are self-recorded; no organization authenticated them.",
        "Instantánea de Relay generada {stamp}. Es una copia de un momento dado, no una vista en vivo. Lista objetivos, estado de aceptación, "
        "responsables, revisores y eventos registrados; no contiene fuentes, paquetes ni entregables. Los nombres los escribió cada persona; ninguna organización los autenticó."),
    "snap.tasks": ("Tasks ({n})", "Tareas ({n})"),
    "snap.no_tasks": ("No tasks yet.", "Todavía no hay tareas."),
    "snap.unreadable": ("This task could not be read and is not shown: {error}", "No se pudo leer esta tarea y no se muestra: {error}"),
    "snap.meta": ("Owner: {owner} · Reviewer: {reviewer} · Revision {revision}", "Responsable: {owner} · Revisión: {reviewer} · Versión {revision}"),

    # ---------------------------------------------------------------- delivery card
    "card.title": ("Delivery card: {goal}", "Tarjeta de entrega: {goal}"),
    "card.html_title": ("Delivery card · {id}", "Tarjeta de entrega · {id}"),
    "card.line": (
        "Task {id} · revision {revision} · {effort} · generated {generated}",
        "Tarea {id} · versión {revision} · {effort} · generada {generated}"),
    "card.h_status": ("Status, in three separate parts", "Estado, en tres partes separadas"),
    "card.sources": ("Selected sources", "Fuentes seleccionadas"),
    "card.work": ("Work returned", "Trabajo entregado"),
    "card.acceptance": ("Acceptance", "Aceptación"),
    "card.h_goal": ("Goal and acceptance criteria", "Objetivo y criterios de aceptación"),
    "card.h_criteria": ("Acceptance criteria", "Criterios de aceptación"),
    "card.boundaries": ("Boundaries: {text}", "Límites: {text}"),
    "card.h_people": ("People (self-recorded)", "Personas (las escribe cada quien)"),
    "card.owner": ("Owner", "Responsable"),
    "card.reviewer": ("Reviewer", "Revisión"),
    "card.owner_sr": ("Owner (self-recorded)", "Responsable (lo escribe cada quien)"),
    "card.reviewer_sr": ("Reviewer (self-recorded)", "Revisión (lo escribe cada quien)"),
    "card.h_sources": ("Selected sources", "Fuentes seleccionadas"),
    "card.t_source": ("Source", "Fuente"),
    "card.t_section": ("Section", "Sección"),
    "card.t_role": ("Role", "Función"),
    "card.t_snapshot": ("Snapshot", "Captura"),
    "card.t_now": ("Now", "Ahora"),
    "card.whole_file": ("whole file", "archivo completo"),
    "card.current": ("current", "vigente"),
    "card.changed": ("changed", "modificada"),
    "card.no_sources": ("No sources were selected beyond the project controls.", "No se seleccionó ninguna fuente además de los controles del proyecto."),
    "card.controls": ("The packet also carries {n} project control file(s).", "El paquete también incluye {n} archivo(s) de control del proyecto."),
    "card.h_work": ("Work returned", "Trabajo entregado"),
    "card.outputs": ("Outputs", "Resultados"),
    "card.evidence": ("Evidence", "Evidencia"),
    "card.copy_of": ("(copy of {path})", "(copia de {path})"),
    "card.changed_since": ("changed since recorded", "modificado desde que se registró"),
    "card.checks": ("Checks the submitter reported (not verified by Relay)", "Comprobaciones que reportó quien entregó (Relay no las verifica)"),
    "card.questions": ("Open questions", "Preguntas abiertas"),
    "card.none_recorded": ("None recorded.", "Ninguna registrada."),
    "card.next": ("Next action (submitter)", "Siguiente acción (quien entregó)"),
    "card.nothing_returned": ("Nothing has been returned for this version.", "No se ha entregado nada para esta versión."),
    "card.blockers": ("Open prerequisites: {blockers}", "Requisitos previos abiertos: {blockers}"),
    "card.h_review": ("Review", "Revisión"),
    "card.accepted_by": ("Accepted by {actor} (self-recorded) at {at}.", "Aceptada por {actor} (autodeclarado) el {at}."),
    "card.changes_by": ("Changes requested by {actor} (self-recorded) at {at}.", "Cambios solicitados por {actor} (autodeclarado) el {at}."),
    "card.reference": ("Reference: {ref} (recorded, not verified).", "Referencia: {ref} (registrada, no verificada)."),
    "card.no_review": ("No review recorded for this version.", "No hay revisión registrada para esta versión."),
    "card.h_ids": ("Identifiers", "Identificadores"),
    "card.packet": ("Packet", "Paquete"),
    "card.submission": ("Submission", "Entrega"),
    "card.none": ("none", "ninguna"),
    "card.note": (
        "Names are self-recorded; no organization authenticated them. Checks are as reported by the submitter and Relay does not verify them. "
        "This card lists what Relay recorded and contains no source, packet or deliverable contents.",
        "Los nombres los escribió cada persona; ninguna organización los autenticó. Las comprobaciones son las que reportó quien entregó y Relay no las verifica. "
        "Esta tarjeta lista lo que Relay registró y no contiene fuentes, paquetes ni entregables."),
}

CATALOGUES: dict[str, dict[str, str]] = {
    "en": {key: pair[0] for key, pair in _PAIRS.items()},
    "es": {key: pair[1] for key, pair in _PAIRS.items()},
}


def normalize(language: str | None) -> str:
    return language if language in LANGUAGES else DEFAULT


def translator(language: str | None = None):
    """Return `t(key, **params)` for a language. An unknown key is a bug in the caller and raises KeyError."""
    catalogue = CATALOGUES[normalize(language)]

    def t(key: str, **params) -> str:
        text = catalogue[key]
        return text.format(**params) if params else text
    return t


def status_label(language: str | None, status: str) -> str:
    return CATALOGUES[normalize(language)].get(f"status.{status}", status)


def profile_label(language: str | None, profile: str) -> str:
    return CATALOGUES[normalize(language)].get(f"profile.{profile}", profile)


def effort(language: str | None, profile: str) -> str:
    return translator(language)("effort", profile=profile_label(language, profile))
