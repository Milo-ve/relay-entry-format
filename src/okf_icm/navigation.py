"""Read-only, deterministic suggestions from a permitted OKF concept graph.

This is a lexical heuristic, not a claim of source sufficiency or verification.
Only explicit start/context selections create packets.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import unicodedata
from urllib.parse import unquote, urlsplit

from . import knowledge, settings
from .i18n import translator
from .packets import headings, section
from .storage import ContextError, contained, read_text
from .tasks import CONTROLS

DEFAULT_MAX_CHARS = 12_000
SOURCE_CAP = 2_000
DEFAULT_LIMIT = 8
BUNDLE = ".context/knowledge"
# Fixed language-neutral scoring with small English/Spanish function-word lists.
STOP = set("""a an the and or of to in on for by as is are be it we our us can do how who
what when where which why with from after before their they this that these those
about into only each at not no than then through your has have will would could should
must need first new also more most all any same some such other both own per each
customer customers write explain check decide prepare produce handle respond answer
summarize draft updated set up asks including get happens say now long did does
el la los las un una unos unas de del al y o en por para con sin que como cuando
donde cual cuales es son se su sus nuestro nuestra nuestros nuestras puede hacer
explica explicar resume resumir escribe escribir sobre""".split())
LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")


def folded(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", value.casefold())
                   if not unicodedata.combining(c))


def tokens(value: str) -> set[str]:
    words = re.findall(r"[^\W_]+", folded(value), flags=re.UNICODE)
    return {w for w in words if len(w) >= 3 and w not in STOP and not w.isdecimal()}


def matches(terms: set[str], value: str) -> set[str]:
    # Substring matching accommodates plurals and compound tags without a stemmer.
    text = folded(value)
    return {word for word in terms if word in text or (word.endswith("s") and len(word) > 4 and word[:-1] in text)}


def _plain(text: str) -> str:
    """Remove fenced code with the same fence convention as packet headings."""
    lines, fence = [], None
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            marker = stripped[:3]
            fence = marker if fence is None else (None if marker == fence else fence)
        elif fence is None:
            lines.append(line)
    return "\n".join(lines)


def _allowed(ws, value: str, deny: list[str], *, missing=False) -> Path | None:
    """Filter spelling and resolved destination before any content read.

    Never return a diagnostic that could reveal an excluded path.
    """
    from .storage import readable
    try:
        settings.check_selection(ws.root, value, deny)
        path = contained(ws.root, value)
        try:
            readable(ws.root, value)
        except FileNotFoundError:
            if not missing:
                return None
        return path
    except (OSError, ValueError, RuntimeError):
        return None


def _catalog(ws, deny):
    bundle = _allowed(ws, BUNDLE, deny)
    if bundle is None or not bundle.is_dir():
        return {}
    concepts = {}
    # Do not descend denied directories, secret paths, or directory symlinks.
    for folder, dirs, files in os.walk(ws.root / BUNDLE, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not (Path(folder) / d).is_symlink()
                         and _allowed(ws, (Path(folder) / d).relative_to(ws.root).as_posix(), deny) is not None)
        for name in sorted(files):
            if not name.endswith(".md") or name in {"index.md", "log.md"}:
                continue
            value = (Path(folder) / name).relative_to(ws.root).as_posix()
            path = _allowed(ws, value, deny)
            if path is None or not path.is_relative_to(bundle):
                continue
            try:
                raw = read_text(ws.root, value)
                meta, body = knowledge.parse_concept(raw)
                if knowledge.validate_meta(meta):
                    continue
                signals = {"lifecycle": meta.get("status", "stable"),
                           "freshness": knowledge.freshness(meta), "trust": knowledge.trust(meta)}
                concepts[value] = {"path": value, "resolved": path, "raw": raw, "body": body,
                                   "meta": meta, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                   "headings": headings(raw), "signals": signals,
                                   "hazard": signals["lifecycle"] != "stable" or signals["freshness"] == "stale"
                                   or signals["trust"] == "unverified"}
            except (OSError, ValueError, UnicodeError):
                continue
    return dict(sorted(concepts.items()))


def _heading(item, fragment: str) -> str | None:
    value = unquote(fragment)
    titles = item["headings"]
    if value in titles:
        return value
    # Contracts and Markdown links commonly use heading slugs; emitted selections
    # always use the exact heading accepted by section(). Ambiguity is not guessed.
    choices = [title for title in titles if folded(re.sub(r"\s+", "-", title)) == folded(value)]
    return choices[0] if len(choices) == 1 else None


def _edges(ws, concepts, deny):
    by_resolved = {item["resolved"]: value for value, item in reversed(list(concepts.items()))}
    edges, missing = {}, []
    bundle = contained(ws.root, BUNDLE)
    for value, item in concepts.items():
        edges[value] = []
        for anchor, target in LINK.findall(_plain(item["body"])):
            try:
                url = urlsplit(target)
                if url.scheme or url.netloc or not url.path:
                    continue
                dest = ((ws.root / BUNDLE / unquote(url.path).lstrip("/")) if url.path.startswith("/")
                        else ws.root / Path(value).parent / unquote(url.path))
                # Relative links may legitimately contain '..'; resolve before the
                # public contained reader, then check both spelling and destination.
                spelled = dest.relative_to(ws.root).as_posix()
                settings.check_selection(ws.root, spelled, deny)
                resolved = dest.resolve()
                if not resolved.is_relative_to(bundle):
                    continue
                relative = resolved.relative_to(ws.root).as_posix()
                if _allowed(ws, relative, deny, missing=True) is None:
                    continue
                found = by_resolved.get(resolved)
                if found:
                    edges[value].append((found, anchor, url.fragment))
                elif not resolved.exists():
                    missing.append((value, anchor, relative))
            except (OSError, ValueError, RuntimeError):
                continue
    return edges, missing


def _named(ws, text, concepts, deny):
    for spec in re.findall(r"`([^`\n]+)`", _plain(text)):
        value, separator, fragment = spec.partition("#")
        # Named inputs are knowledge concepts only, never arbitrary artifacts.
        if value not in concepts or _allowed(ws, value, deny) is None:
            continue
        title = _heading(concepts[value], fragment) if separator else None
        if separator and title is None:
            continue
        yield value, title


def source_record(item, title):
    """The exact task file record; hashes cover the full file even for sections."""
    return {"path": item["path"], "section": title, "role": "knowledge",
            "sha256": item["sha256"],
            "content": section(item["raw"], title) if title else item["raw"],
            "knowledge_signals": item["signals"]}


def source_characters(record):
    # JSON pretty-print indentation must match Tasks.render_packet, including the
    # comma separating adjacent records. This is an additive source-only budget.
    return len(json.dumps(record, ensure_ascii=False, indent=2).replace("\n", "\n    ")) + 6


def navigate(ws, goal: str, *, stage: str | None = None,
             max_chars: int = DEFAULT_MAX_CHARS, limit: int = DEFAULT_LIMIT) -> dict:
    if not isinstance(goal, str) or not goal.strip():
        raise ContextError("navigate needs a nonempty goal.")
    if type(max_chars) is not int or not 1 <= max_chars <= 1_000_000:
        raise ContextError("navigate max-chars must be from 1 to 1000000.")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ContextError("navigate limit must be from 1 to 100.")
    config = settings.load(ws.home)
    deny, language = config["deny_paths"], config["language"]
    t = translator(language)

    def message(code, **params):
        return {"code": code, "params": params, "text": t("nav." + code, **params)}

    # Validate stage before scanning. No run or dependency completion is implied.
    contract = ws.stage(stage)["contract"] if stage is not None else None
    concepts = _catalog(ws, deny)
    terms = tokens(goal)
    fields = (("tags", 12), ("title", 10), ("heading", 6), ("description", 5), ("body", 1))
    for value, item in concepts.items():
        meta = item["meta"]
        values = {"tags": " ".join(meta.get("tags", [])), "title": str(meta.get("title", Path(value).stem)),
                  "heading": " ".join(item["headings"]), "description": str(meta.get("description", "")),
                  "body": _plain(item["body"])}
        item["hits"] = {field: matches(terms, values[field]) for field, _ in fields}
        item["all_hits"] = set().union(*item["hits"].values())
    counts = Counter(term for item in concepts.values() for term in item["all_hits"])
    weight = {term: min(4, max(1, (len(concepts) + 1) // (count + 1))) for term, count in counts.items()}
    seeds, why, preferred, contract_named = {}, {}, {}, set()
    for value, item in concepts.items():
        item["score"] = sum(base * weight[word] for field, base in fields for word in item["hits"][field])
        structured = set().union(*(item["hits"][field] for field, _ in fields if field != "body"))
        why[value] = [message("match", field=field, terms=", ".join(sorted(item["hits"][field])))
                      for field, _ in fields if item["hits"][field]]
        if structured:
            seeds[value] = item["score"]
    for control in (".context/ENTRY.md", ".context/project.md"):
        # Controls are explicit workflow inputs, but their prose is never executed.
        for value, title in _named(ws, read_text(ws.root, control), concepts, deny):
            if value in seeds:
                seeds[value] += 4
                why[value].append(message("entry_named", source=control))
                if title:
                    preferred.setdefault(value, set()).add(title)
    if contract:
        text = read_text(ws.root, contract)
        try:
            inputs = section(text, "Inputs")
        except ContextError:
            inputs = ""
        for value, title in _named(ws, inputs, concepts, deny):
            contract_named.add(value)
            seeds[value] = max(seeds.get(value, 0), 1000)
            why[value].append(message("contract_named", source=contract))
            if title:
                preferred.setdefault(value, set()).add(title)
    best = max((score for value, score in seeds.items() if value not in contract_named), default=0)
    bar = max(10, best * 0.35)
    strong = {value: score for value, score in seeds.items() if score >= bar or value in contract_named}
    edges, unresolved = _edges(ws, concepts, deny)
    indegree = Counter(dest for links in edges.values() for dest in {e[0] for e in links})
    ranked = dict(strong)
    hubs = set()
    # Exactly one hop, from the original strong seeds, never recursively from links.
    for source, score in sorted(strong.items()):
        for value, anchor, fragment in edges[source]:
            supported = bool(matches(terms, anchor + " " + unquote(fragment)))
            if indegree[value] > max(3, len(concepts) * 0.25) and not supported:
                hubs.add(value)
                continue
            item = concepts[value]
            if not supported and not item["all_hits"]:
                continue
            link_score = score * 0.4 + item["score"] * 0.5
            if supported:
                link_score = max(bar, link_score)
            if link_score < bar and value not in ranked:
                continue
            ranked[value] = max(ranked.get(value, 0), link_score)
            why[value].append(message("link", source=source))
            title = _heading(item, fragment) if fragment else None
            if title:
                preferred.setdefault(value, set()).add(title)
    stable_hits = set().union(*(concepts[value]["all_hits"] for value in ranked if not concepts[value]["hazard"])) if ranked else set()
    selected, left, used = [], [], 0
    order = sorted(concepts, key=lambda value: (value not in contract_named, concepts[value]["hazard"],
                                               -ranked.get(value, seeds.get(value, 0)), value))
    for value in order:
        item = concepts[value]
        reason = None
        if value not in ranked:
            reason = "hub" if value in hubs else "below_bar"
        elif item["hazard"] and not (item["all_hits"] - stable_hits) and value not in contract_named:
            reason = "covered_hazard"
        titles = item["headings"]
        duplicate = len(titles) != len(set(titles))
        wanted = sorted(preferred.get(value, set()))
        if not wanted and not duplicate:
            # Ignore the title heading that spans the complete body. Use a single
            # focussed section when heading matches are concentrated there.
            sub = [title for title in titles if not section(item["raw"], title).lstrip().startswith("# ")]
            scores = {title: sum(weight.get(word, 1) for word in matches(terms, title)) for title in sub}
            positive = [title for title in sub if scores[title]]
            if len(positive) == 1:
                wanted = positive
            elif len(item["raw"]) > SOURCE_CAP:
                wanted = sorted(positive, key=lambda title: (-scores[title], title))
        if duplicate:
            wanted = []
        specs = wanted or [None]
        for title in specs:
            record = source_record(item, title)
            raw_chars = len(record["content"])
            chars = source_characters(record)
            entry = {"select": value + ("#" + title if title else ""), "characters": chars,
                     "raw_characters": raw_chars, "score": round(ranked.get(value, seeds.get(value, 0)), 3),
                     "why": why[value], "warnings": [message("signals", **item["signals"])] if item["hazard"] else [],
                     "signals": item["signals"]}
            if duplicate:
                entry["warnings"].append(message("duplicate_heading"))
            omitted = reason
            if omitted is None and raw_chars > SOURCE_CAP:
                omitted = "source_cap"
            if omitted is None and used + chars > max_chars:
                omitted = "over_budget"
            if omitted is None and len(selected) >= limit:
                omitted = "limit"
            if omitted:
                entry["reason"] = message(omitted)
                left.append(entry)
            else:
                selected.append(entry)
                used += chars
    gaps = [message("unmatched", term=word) for word in sorted(terms - counts.keys())]
    if not strong:
        gaps.append(message("no_coverage"))
    elif not selected:
        gaps.append(message("no_selection"))
    for source, anchor, target in sorted(set(unresolved)):
        if matches(terms, anchor) and (source in ranked or not strong):
            gaps.append(message("missing_link", source=source, target=target))
    notes = [message("candidates"), message("excluded")]
    if max_chars > 26_000:
        notes.append(message("ceiling"))
    # Indexes are derived and may lag. Only inspect safe index files; names and
    # counts of excluded concepts never enter this diagnostic.
    indexed = set()
    for value, item in concepts.items():
        index = (Path(value).parent / "index.md").as_posix()
        if _allowed(ws, index, deny) is not None:
            try:
                for _, target in LINK.findall(_plain(read_text(ws.root, index))):
                    url = urlsplit(target)
                    if not url.scheme and url.path:
                        indexed.add((ws.root / Path(index).parent / unquote(url.path)).resolve())
            except (OSError, ValueError, UnicodeError):
                pass
    not_indexed = sum(item["resolved"] not in indexed for item in concepts.values())
    notes.append(message("index", count=not_indexed))
    # Report raw controls separately; they are never charged to the source budget.
    controls_chars = sum(len(read_text(ws.root, value)) for value in CONTROLS)
    return {"candidates": selected, "left_out": left[:limit], "left_out_remaining": max(0, len(left) - limit),
            "budget": {"used": used, "max_chars": max_chars, "unit": "task-packet-characters",
                       "per_source_raw_chars": SOURCE_CAP, "controls_raw_chars": controls_chars},
            "gaps": gaps, "notes": notes}
